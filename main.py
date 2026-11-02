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
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("harry-backend")

app = FastAPI(title="harry-nifty Pro Automated Bridge")

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
        logger.info("Token saved to disk.")
    except Exception as e:
        logger.error(f"Error saving token: {e}")

PUBLIC_ACCESS_TOKEN = load_saved_token()

# Initial Cache
live_market_cache: Dict[str, Dict[str, Any]] = {
    "NIFTY": {"ltp": 23222.10, "vwap": 23295.00, "high": 23360.00, "low": 23210.00, "close": 23310.00, "pcr": 0.92, "rsi": 41.5},
    "BANKNIFTY": {"ltp": 51840.10, "vwap": 51950.00, "high": 52100.00, "low": 51720.00, "close": 51890.00, "pcr": 0.86, "rsi": 58.2},
    "SENSEX": {"ltp": 80120.50, "vwap": 79950.00, "high": 80300.00, "low": 79800.00, "close": 80000.00, "pcr": 1.30, "rsi": 61.0},
    "FINNIFTY": {"ltp": 23910.80, "vwap": 23890.00, "high": 24020.00, "low": 23840.00, "close": 23900.00, "pcr": 1.08, "rsi": 55.4},
    "RELIANCE": {"ltp": 1252.50, "vwap": 1258.00, "high": 1265.00, "low": 1240.00, "close": 1255.00, "pcr": 1.31, "rsi": 62.1},
    "HDFCBANK": {"ltp": 689.20, "vwap": 693.00, "high": 695.00, "low": 680.00, "close": 690.00, "pcr": 0.82, "rsi": 49.8}
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

    logger.info(f"Callback received requestToken: {requestToken}")
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
                logger.info("Public Access Token successfully acquired and saved!")
                return HTMLResponse("""
                    <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:60px;">
                        <h2>✅ FULLY AUTOMATED FEED ACTIVATED!</h2>
                        <p style="color:#94a3b8;">Token permanently saved.</p>
                        <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px;">Open Trading Terminal</a>
                    </body>
                """)
            else:
                return HTMLResponse(f"<h3 style='color:red;'>Token Error: {res_data}</h3>", status_code=400)
        except Exception as exc:
            return HTMLResponse(f"<h3 style='color:red;'>Exception: {exc}</h3>", status_code=500)

def update_cache_price(security_id: int, price: float, high: float = 0, low: float = 0, close: float = 0):
    price_val = round(float(price), 2)
    if price_val <= 0:
        return

    sym_key = ""
    if security_id == 13:
        sym_key = "NIFTY"
    elif security_id == 25:
        sym_key = "BANKNIFTY"
    elif security_id == 2885:
        sym_key = "RELIANCE"
    elif security_id == 1333:
        sym_key = "HDFCBANK"

    if sym_key:
        live_market_cache[sym_key]["ltp"] = price_val
        
        # Keep real high/low/close bounds
        if high > 0: live_market_cache[sym_key]["high"] = round(float(high), 2)
        if low > 0: live_market_cache[sym_key]["low"] = round(float(low), 2)
        if close > 0: live_market_cache[sym_key]["close"] = round(float(close), 2)
        
        # True Typical Price VWAP
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
            if packet_type == 64 or packet_type == 61:
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 8)[0]
                pos += 22
                update_cache_price(security_id, last_price)
            elif packet_type == 65:
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 4)[0]
                c = struct.unpack_from('<f', data, pos + 14)[0]
                h = struct.unpack_from('<f', data, pos + 18)[0]
                l = struct.unpack_from('<f', data, pos + 22)[0]
                pos += 42
                update_cache_price(security_id, last_price, h, l, c)
            elif packet_type == 66:
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<i', data, pos + 4)[0]
                c = struct.unpack_from('<f', data, pos + 14)[0]
                h = struct.unpack_from('<f', data, pos + 18)[0]
                l = struct.unpack_from('<f', data, pos + 22)[0]
                pos += 38
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
                logger.info("Opening WebSocket connection to Paytm Live Streamer...")
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    subscription_packet = [
                        {"actionType": "ADD", "modeType": "FULL", "scripType": "INDEX", "exchangeType": "NSE", "scripId": "13"},
                        {"actionType": "ADD", "modeType": "FULL", "scripType": "INDEX", "exchangeType": "NSE", "scripId": "25"},
                        {"actionType": "ADD", "modeType": "LTP", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "2885"},
                        {"actionType": "ADD", "modeType": "LTP", "scripType": "EQUITY", "exchangeType": "NSE", "scripId": "1333"}
                    ]
                    await ws.send(json.dumps(subscription_packet))
                    logger.info("Active subscription running!")
                    while True:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            parse_paytm_binary_packet(msg)
            except Exception as exc:
                logger.warning(f"Paytm WS reconnecting: {exc}")
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(paytm_websocket_client())

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
