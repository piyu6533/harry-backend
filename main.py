import asyncio
import json
import logging
import os
import struct
from typing import Dict, Any
import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("harry-backend")

app = FastAPI(title="harry-nifty Pro Fully Automated Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY: str = "b29e5048f9ab47bc9ff6a33f4d1fceb9"
API_SECRET: str = "17fce6cce6ca45548ba54db681d8846c"
TOKEN_FILE = "token_session.json"

PUBLIC_ACCESS_TOKEN: str = ""

def load_saved_token() -> str:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("public_access_token", "")
        except Exception as e:
            logger.error(f"Error reading token file: {e}")
    return ""

def save_token_to_disk(token: str):
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"public_access_token": token}, f)
        logger.info("Token successfully saved to disk.")
    except Exception as e:
        logger.error(f"Error saving token: {e}")

PUBLIC_ACCESS_TOKEN = load_saved_token()

# True Market Cache (Updated to active index levels)
live_market_cache: Dict[str, Dict[str, Any]] = {
    "NIFTY": {"ltp": 23440.80, "vwap": 23415.00, "high": 23485.00, "low": 23320.00, "close": 23440.80, "pcr": 0.96},
    "BANKNIFTY": {"ltp": 55002.20, "vwap": 54950.00, "high": 55150.00, "low": 54720.00, "close": 55002.20, "pcr": 0.90},
    "RELIANCE": {"ltp": 1265.40, "vwap": 1262.00, "high": 1272.00, "low": 1250.00, "close": 1265.40, "pcr": 1.25},
    "HDFCBANK": {"ltp": 694.80, "vwap": 692.00, "high": 698.00, "low": 688.00, "close": 694.80, "pcr": 0.88}
}

connected_websockets = set()

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "harry-nifty-backend",
        "token_active": bool(PUBLIC_ACCESS_TOKEN),
        "live_cache": live_market_cache
    }

@app.get("/login")
def login_redirect():
    login_url = f"https://login.paytmmoney.com/merchant-login?apiKey={API_KEY}"
    return RedirectResponse(login_url)

@app.get("/callback")
async def paytm_callback(requestToken: str = Query(None)):
    global PUBLIC_ACCESS_TOKEN
    if not requestToken:
        return HTMLResponse("<h3 style='color:red;'>Missing requestToken</h3>", status_code=400)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_response = await client.post(
                "https://developer.paytmmoney.com/accounts/v2/gettoken",
                json={
                    "api_key": API_KEY,
                    "api_secret_key": API_SECRET,
                    "request_token": requestToken
                }
            )
            res_data = token_response.json()
            pub_token = res_data.get("public_access_token") or res_data.get("data", {}).get("public_access_token")
            if not pub_token:
                pub_token = res_data.get("access_token") or res_data.get("data", {}).get("access_token")

            if pub_token:
                PUBLIC_ACCESS_TOKEN = pub_token
                save_token_to_disk(pub_token)
                return HTMLResponse("""
                    <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:60px;">
                        <h2>✅ FULLY AUTOMATED FEED ACTIVATED!</h2>
                        <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px;">Open Terminal</a>
                    </body>
                """)
            else:
                return HTMLResponse(f"<h3 style='color:red;'>Token Error: {res_data}</h3>", status_code=400)
        except Exception as exc:
            return HTMLResponse(f"<h3 style='color:red;'>Exception: {exc}</h3>", status_code=500)

# AUTOMATED FAILOVER QUOTE SYNC ENGINE
async def auto_market_quote_sync():
    """Fetches official live closing/current prices continuously so values never get stuck."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                resp = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m")
                if resp.status_code == 200:
                    meta = resp.json()["chart"]["result"][0]["meta"]
                    cur_p = round(float(meta.get("regularMarketPrice", 0.0)), 2)
                    day_h = round(float(meta.get("regularMarketDayHigh", cur_p)), 2)
                    day_l = round(float(meta.get("regularMarketDayLow", cur_p)), 2)
                    prev_c = round(float(meta.get("previousClose", cur_p)), 2)
                    if cur_p > 0:
                        live_market_cache["NIFTY"]["ltp"] = cur_p
                        live_market_cache["NIFTY"]["high"] = day_h
                        live_market_cache["NIFTY"]["low"] = day_l
                        live_market_cache["NIFTY"]["close"] = prev_c
                        if day_h > day_l:
                            live_market_cache["NIFTY"]["vwap"] = round((day_h + day_l + cur_p) / 3.0, 2)
        except Exception:
            pass
        await asyncio.sleep(4)

# PAYTM OFFICIAL OPTION CHAIN BRIDGE (Fix: fetches CALL and PUT concurrently)
@app.get("/api/option-chain")
async def get_paytm_option_chain(symbol: str = "NIFTY", expiry: str = "03-11-2026"):
    token = PUBLIC_ACCESS_TOKEN or load_saved_token()
    if not token:
        return JSONResponse({"status": "no_token", "message": "Using live greeks fallback"}, status_code=200)

    headers = {"x-jwt-token": token, "Accept": "application/json"}
    call_url = f"https://developer.paytmmoney.com/fno/v1/option-chain?type=CALL&symbol={symbol}&expiry={expiry}"
    put_url = f"https://developer.paytmmoney.com/fno/v1/option-chain?type=PUT&symbol={symbol}&expiry={expiry}"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            call_resp, put_resp = await asyncio.gather(
                client.get(call_url, headers=headers),
                client.get(put_url, headers=headers),
                return_exceptions=True
            )

            call_data = call_resp.json().get("data", []) if hasattr(call_resp, "json") and call_resp.status_code == 200 else []
            put_data = put_resp.json().get("data", []) if hasattr(put_resp, "json") and put_resp.status_code == 200 else []

            # Merge by strike price
            merged = {}
            for c in call_data:
                stk = float(c.get("stk_price", 0))
                if stk > 0:
                    merged[stk] = {
                        "strike_price": stk,
                        "call_price": c.get("price"),
                        "call_oi": c.get("oi"),
                        "put_price": None,
                        "put_oi": None
                    }

            for p in put_data:
                stk = float(p.get("stk_price", 0))
                if stk > 0:
                    if stk not in merged:
                        merged[stk] = {
                            "strike_price": stk,
                            "call_price": None,
                            "call_oi": None,
                            "put_price": p.get("price"),
                            "put_oi": p.get("oi")
                        }
                    else:
                        merged[stk]["put_price"] = p.get("price")
                        merged[stk]["put_oi"] = p.get("oi")

            sorted_chain = sorted(merged.values(), key=lambda x: x["strike_price"])
            return JSONResponse({"status": "success", "data": sorted_chain})
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)})

def update_cache_price(security_id: int, price: float, high: float = 0, low: float = 0, close: float = 0):
    price_val = round(float(price), 2)
    if price_val <= 0:
        return

    sym_key = ""
    if security_id == 13: sym_key = "NIFTY"
    elif security_id == 25: sym_key = "BANKNIFTY"
    elif security_id == 2885: sym_key = "RELIANCE"
    elif security_id == 1333: sym_key = "HDFCBANK"

    if sym_key:
        live_market_cache[sym_key]["ltp"] = price_val
        if high > 0: live_market_cache[sym_key]["high"] = round(float(high), 2)
        if low > 0: live_market_cache[sym_key]["low"] = round(float(low), 2)
        if close > 0: live_market_cache[sym_key]["close"] = round(float(close), 2)
        cur_h = live_market_cache[sym_key].get("high", price_val)
        cur_l = live_market_cache[sym_key].get("low", price_val)
        cur_c = live_market_cache[sym_key].get("close", price_val)
        if cur_h > cur_l:
            live_market_cache[sym_key]["vwap"] = round((cur_h + cur_l + cur_c) / 3.0, 2)

def parse_paytm_binary_packet(data: bytes):
    length = len(data)
    pos = 0
    while pos < length:
        packet_type = data[pos]
        pos += 1
        try:
            if packet_type in (64, 61):
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 8)[0]
                pos += 22
                update_cache_price(security_id, last_price)
            elif packet_type in (65, 66):
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 4)[0]
                c = struct.unpack_from('<f', data, pos + 14)[0]
                h = struct.unpack_from('<f', data, pos + 18)[0]
                l = struct.unpack_from('<f', data, pos + 22)[0]
                pos += (42 if packet_type == 65 else 38)
                update_cache_price(security_id, last_price, h, l, c)
            elif packet_type == 62:
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 8)[0]
                pos += 66
                update_cache_price(security_id, last_price)
            elif packet_type == 63:
                pos += 100
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 8)[0]
                pos += 74
                update_cache_price(security_id, last_price)
            else:
                break
        except Exception:
            break

async def paytm_websocket_client():
    while True:
        token = PUBLIC_ACCESS_TOKEN or load_saved_token()
        if token:
            ws_url = f"wss://developer-ws.paytmmoney.com/broadcast/user/v1/data?x_jwt_token={token}"
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    subscription_packet = [
                        {"actionType": "ADD", "modeType": "FULL", "scripType": "INDEX", "exchangeType": "NSE", "scripId": "13"},
                        {"actionType": "ADD", "modeType": "FULL", "scripType": "INDEX", "exchangeType": "NSE", "scripId": "25"},
                        {"actionType": "ADD", "modeType": "LTP", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "2885"},
                        {"actionType": "ADD", "modeType": "LTP", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "1333"}
                    ]
                    await ws.send(json.dumps(subscription_packet))
                    while True:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            parse_paytm_binary_packet(msg)
            except Exception:
                pass
        await asyncio.sleep(4)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(paytm_websocket_client())
    asyncio.create_task(auto_market_quote_sync())

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            await websocket.send_text(json.dumps({
                "type": "TICK_UPDATE",
                "data": live_market_cache
            }))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_websockets.discard(websocket)
    except Exception:
        connected_websockets.discard(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
