import asyncio
import json
import logging
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

app = FastAPI(title="harry-nifty Backend Terminal Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paytm Money Credentials
API_KEY: str = "b29e5048f9ab47bc9ff6a33f4d1fceb9"
API_SECRET: str = "17fce6cce6ca45548ba54db681d8846c"

PUBLIC_ACCESS_TOKEN: str = ""

# Live Cache for Terminal
live_market_cache: Dict[str, Dict[str, Any]] = {
    "NIFTY": {"ltp": 24380.40, "vwap": 24320.00, "pcr": 1.24, "rsi": 64.5},
    "BANKNIFTY": {"ltp": 51840.10, "vwap": 51950.00, "pcr": 0.86, "rsi": 58.2},
    "SENSEX": {"ltp": 80120.50, "vwap": 79950.00, "pcr": 1.30, "rsi": 61.0},
    "FINNIFTY": {"ltp": 23910.80, "vwap": 23890.00, "pcr": 1.08, "rsi": 55.4},
    "RELIANCE": {"ltp": 2890.50, "vwap": 2872.00, "pcr": 1.31, "rsi": 62.1},
    "HDFCBANK": {"ltp": 1682.20, "vwap": 1690.00, "pcr": 0.82, "rsi": 49.8}
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
            
            # Paytm provides access_token and public_access_token
            pub_token = res_data.get("public_access_token") or res_data.get("data", {}).get("public_access_token")
            if not pub_token:
                pub_token = res_data.get("access_token") or res_data.get("data", {}).get("access_token")

            if pub_token:
                PUBLIC_ACCESS_TOKEN = pub_token
                logger.info("Public Access Token successfully acquired! Connecting WebSocket Streamer...")
                return HTMLResponse("""
                    <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:60px;">
                        <h2>✅ LIVE WEBSOCKET FEED ACTIVATED!</h2>
                        <p style="color:#94a3b8;">Paytm Market Data Streamer is now running.</p>
                        <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px;">Open Trading Terminal</a>
                    </body>
                """)
            else:
                logger.error(f"Failed getting token: {res_data}")
                return HTMLResponse(f"<h3 style='color:red;'>Token Error: {res_data}</h3>", status_code=400)
        except Exception as exc:
            logger.error(f"Callback exception: {exc}")
            return HTMLResponse(f"<h3 style='color:red;'>Exception: {exc}</h3>", status_code=500)


def parse_paytm_binary_packet(data: bytes):
    """Parses binary byte buffer from Paytm Live Market Data Stream."""
    length = len(data)
    pos = 0
    while pos < length:
        packet_type = data[pos]
        pos += 1

        try:
            # Type 64: INDEX LTP (Size: 22 bytes after type)
            if packet_type == 64:
                last_price, last_update_time, security_id, tradable, mode, change_abs, change_pct = struct.unpack_from('<fiIbBff', data, pos)
                pos += 22
                update_cache_price(security_id, last_price)

            # Type 65: INDEX QUOTE (Size: 42 bytes)
            elif packet_type == 65:
                last_price, security_id, tradable, mode, o, c, h, l, chg_pct, chg_abs, high_52, low_52 = struct.unpack_from('<fIbBffffff', data, pos)
                pos += 42
                update_cache_price(security_id, last_price)

            # Type 66: INDEX FULL (Size: 38 bytes)
            elif packet_type == 66:
                last_price, security_id, tradable, mode, o, c, h, l, chg_pct, chg_abs, last_time = struct.unpack_from('<fIbBfffffI', data, pos)
                pos += 38
                update_cache_price(security_id, last_price)

            # Type 61: EQUITY LTP (Size: 22 bytes)
            elif packet_type == 61:
                last_price, last_traded_time, security_id, tradable, mode, change_abs, change_pct = struct.unpack_from('<fiIbBff', data, pos)
                pos += 22
                update_cache_price(security_id, last_price)

            # Type 62: EQUITY QUOTE (Size: 66 bytes)
            elif packet_type == 62:
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<I', data, pos + 8)[0]
                pos += 66
                update_cache_price(security_id, last_price)

            # Type 63: FULL PACKET (100 bytes depth + 74 bytes data = 174 bytes)
            elif packet_type == 63:
                pos += 100  # Skip market depth
                last_price = struct.unpack_from('<f', data, pos)[0]
                security_id = struct.unpack_from('<I', data, pos + 8)[0]
                pos += 74
                update_cache_price(security_id, last_price)
            else:
                # If unknown byte type encountered, safely break out
                break
        except Exception as parse_err:
            logger.debug(f"Parsing error on packet {packet_type}: {parse_err}")
            break


def update_cache_price(security_id: int, price: float):
    price_val = round(float(price), 2)
    if security_id == 13:
        live_market_cache["NIFTY"]["ltp"] = price_val
        live_market_cache["NIFTY"]["vwap"] = price_val
        logger.info(f"⚡ [Paytm Feed] NIFTY 50 Live: {price_val}")
    elif security_id == 25:
        live_market_cache["BANKNIFTY"]["ltp"] = price_val
        live_market_cache["BANKNIFTY"]["vwap"] = price_val
        logger.info(f"⚡ [Paytm Feed] BANKNIFTY Live: {price_val}")
    elif security_id == 2885:
        live_market_cache["RELIANCE"]["ltp"] = price_val
    elif security_id == 1333:
        live_market_cache["HDFCBANK"]["ltp"] = price_val


async def paytm_websocket_client():
    """Persistent background client streaming from Paytm Live Broadcast WS."""
    while True:
        if PUBLIC_ACCESS_TOKEN:
            ws_url = f"wss://developer-ws.paytmmoney.com/broadcast/user/v1/data?x_jwt_token={PUBLIC_ACCESS_TOKEN}"
            try:
                logger.info("Opening WebSocket connection to Paytm Live Streamer...")
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    logger.info("Connected to Paytm Live Broadcast API!")

                    # Subscription Preferences
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
                    logger.info("Sent subscription packet for NIFTY, BANKNIFTY, RELIANCE, HDFCBANK")

                    while True:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            parse_paytm_binary_packet(msg)
                        else:
                            logger.info(f"Paytm WS Text: {msg}")

            except websockets.exceptions.ConnectionClosed as cc:
                logger.warning(f"Paytm WS connection closed: {cc}. Reconnecting in 3 seconds...")
            except Exception as exc:
                logger.error(f"Paytm WS Exception: {exc}. Reconnecting in 3 seconds...")

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
        connected_websockets.remove(websocket)
    except Exception:
        connected_websockets.discard(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
