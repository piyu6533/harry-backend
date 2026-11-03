import asyncio
import json
import logging
import os
import struct
import math
from typing import Dict, Any
import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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

API_KEY = os.getenv("PAYTM_API_KEY", "").strip()
API_SECRET = os.getenv("PAYTM_API_SECRET", "").strip()

if not API_KEY or not API_SECRET:
    logger.warning("Paytm API credentials are not configured.")
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

live_market_cache: Dict[str, Dict[str, Any]] = {
    "NIFTY": {"ltp": 23591.70, "vwap": 23511.43, "high": 23610.70, "low": 23482.80, "close": 23440.80, "pcr": 0.96},
    "BANKNIFTY": {"ltp": 55322.40, "vwap": 55221.08, "high": 55486.95, "low": 55174.10, "close": 55002.20, "pcr": 0.90},
    "RELIANCE": {"ltp": 1301.40, "vwap": 1262.47, "high": 1272.00, "low": 1250.00, "close": 1265.40, "pcr": 1.25},
    "HDFCBANK": {"ltp": 712.70, "vwap": 693.60, "high": 698.00, "low": 688.00, "close": 694.80, "pcr": 0.88}
}

connected_websockets = set()

def normal_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def bs_price(S, K, T, v, opt_type):
    if T <= 0.0005:
        T = 0.0005
    d1 = (math.log(S / K) + (v * v / 2.0) * T) / (v * math.sqrt(T))
    d2 = d1 - v * math.sqrt(T)
    if opt_type == 'CE':
        return max(0.50, round(S * normal_cdf(d1) - K * normal_cdf(d2), 2))
    else:
        return max(0.50, round(K * normal_cdf(-d2) - S * normal_cdf(-d1), 2))

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

@app.get("/api/option-chain")
async def get_live_option_chain(symbol: str = "NIFTY", expiry: str = "03-Nov-2026"):
    asset = live_market_cache.get(symbol, live_market_cache["NIFTY"])
    spot = asset.get("ltp", 23591.70)
    step = 50 if symbol == "NIFTY" else (100 if symbol == "BANKNIFTY" else 20)
    atm = round(spot / step) * step

    dte_days = 0.5
    if "09-Nov" in expiry:
        dte_days = 6.5
    elif "23-Nov" in expiry:
        dte_days = 20.5

    T = dte_days / 365.0
    iv = 0.1550

    strikes_data = []
    for i in range(-4, 5):
        strike = atm + (i * step)
        c_price = bs_price(spot, strike, T, iv, 'CE')
        p_price = bs_price(spot, strike, T, iv, 'PE')
        c_oi = round(max(10.0, 185.0 - abs(strike - atm) * 0.35), 1)
        p_oi = round(max(10.0, 192.0 - abs(strike - atm) * 0.38), 1)

        strikes_data.append({
            "strike_price": strike,
            "call_price": c_price,
            "call_oi": c_oi,
            "put_price": p_price,
            "put_oi": p_oi
        })

    return JSONResponse({"status": "success", "spot": spot, "atm": atm, "data": strikes_data})

# Continuous Live Poller: Live tick sync ensure karega
async def live_quote_poller():
    headers = {"User-Agent": "Mozilla/5.0"}
    while True:
        try:
            async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
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
        await asyncio.sleep(2)

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

    if not data:
        logger.warning("Paytm received an empty packet.")
        return

    logger.info(
        "Paytm packet diagnostic: length=%s, first_byte=%s",
        length,
        data[0]
    )

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
                logger.warning(
                    "Unknown Paytm packet type: %s",
                    packet_type
                )
                break

        except (struct.error, IndexError, ValueError):
            logger.exception(
                "Paytm packet parsing failed: type=%s, position=%s, length=%s",
                packet_type,
                pos,
                length
            )
            break


async def paytm_websocket_client():
    while True:
        token = PUBLIC_ACCESS_TOKEN or load_saved_token()

        if not token:
            logger.warning("Paytm token unavailable. Waiting for login.")
            await asyncio.sleep(10)
            continue

        ws_url = (
            "wss://developer-ws.paytmmoney.com/"
            "broadcast/user/v1/data?x_jwt_token=" + token
        )

        try:
            logger.info("Connecting to Paytm WebSocket...")

            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=20
            ) as ws:

                logger.info("Paytm WebSocket CONNECTED")

                subscription_packet = [
                    {
                        "actionType": "ADD",
                        "modeType": "FULL",
                        "scripType": "INDEX",
                        "exchangeType": "NSE",
                        "scripId": "13"
                    },
                    {
                        "actionType": "ADD",
                        "modeType": "FULL",
                        "scripType": "INDEX",
                        "exchangeType": "NSE",
                        "scripId": "25"
                    },
                    {
                        "actionType": "ADD",
                        "modeType": "LTP",
                        "scripType": "EQUITY",
                        "exchangeType": "NSE",
                        "scripId": "2885"
                    },
                    {
                        "actionType": "ADD",
                        "modeType": "LTP",
                        "scripType": "EQUITY",
                        "exchangeType": "NSE",
                        "scripId": "1333"
                    }
                ]

                await ws.send(json.dumps(subscription_packet))
                logger.info("Paytm subscription request sent.")

                first_packet_logged = False

                while True:
                    msg = await ws.recv()

                    if isinstance(msg, bytes):
                        if not first_packet_logged:
                            logger.info(
                                "First binary market packet received: %s bytes",
                                len(msg)
                            )
                            first_packet_logged = True

                        parse_paytm_binary_packet(msg)

                    else:
                        logger.info(
                            "Paytm non-binary message received: %s",
                            str(msg)[:150]
                        )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            logger.exception("Paytm WebSocket connection error: %s", exc)

        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    logger.info("APP STARTUP EVENT TRIGGERED")

    logger.info(
        "Paytm token available at startup: %s",
        bool(PUBLIC_ACCESS_TOKEN or load_saved_token())
    )

    app.state.paytm_task = asyncio.create_task(
        paytm_websocket_client()
    )

    app.state.yahoo_task = asyncio.create_task(
        live_quote_poller()
    )

    logger.info("Paytm WebSocket background task created.")
    logger.info("Yahoo poller background task created.")

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
