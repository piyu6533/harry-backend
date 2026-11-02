import asyncio
import json
import logging
from typing import Dict, Any
import httpx
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

API_KEY: str = "b29e5048f9ab47bc9ff6a33f4d1fceb9"
API_SECRET: str = "17fce6cce6ca45548ba54db681d8846c"

ACCESS_TOKEN: str = ""

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
        "access_token_active": bool(ACCESS_TOKEN),
        "live_cache": live_market_cache
    }


@app.get("/login")
def login_redirect():
    login_url = f"https://login.paytmmoney.com/merchant-login?apiKey={API_KEY}"
    return RedirectResponse(login_url)


@app.get("/callback")
async def paytm_callback(requestToken: str = Query(None)):
    global ACCESS_TOKEN
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
            token = res_data.get("data", {}).get("access_token") or res_data.get("access_token")

            if token:
                ACCESS_TOKEN = token
                logger.info(f"Access Token generated successfully! (Length: {len(token)})")
                return HTMLResponse("""
                    <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:60px;">
                        <h2>✅ LIVE FEED ACTIVATED!</h2>
                        <p style="color:#94a3b8;">Paytm Money Access Token successfully loaded.</p>
                        <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px;">Open Trading Terminal</a>
                    </body>
                """)
            else:
                logger.error(f"Token generation error: {res_data}")
                return HTMLResponse(f"<h3 style='color:red;'>Token Generation Failed: {res_data}</h3>", status_code=400)
        except Exception as exc:
            logger.error(f"Callback Exception: {exc}")
            return HTMLResponse(f"<h3 style='color:red;'>Internal Error: {str(exc)}</h3>", status_code=500)


@app.get("/set-token")
def set_token(token: str):
    global ACCESS_TOKEN
    ACCESS_TOKEN = token.strip()
    return {"message": "Access Token updated successfully", "status": "LIVE"}


async def fetch_paytm_live_quotes():
    """Fetches real quotes from Paytm Money's active /data/v1/quotes/value endpoint."""
    # Official Paytm Money Quote Endpoint
    quote_url = "https://developer.paytmmoney.com/data/v1/quotes/value"
    
    # Official format: Exchange:SecurityId:InstrumentType
    params = {
        "pref": "NSE:13:INDEX,NSE:25:INDEX,NSE:2885:EQUITY,NSE:1333:EQUITY"
    }

    async with httpx.AsyncClient(timeout=4.0) as client:
        while True:
            if ACCESS_TOKEN:
                headers = {
                    "x-jwt-token": ACCESS_TOKEN,
                    "Content-Type": "application/json"
                }
                try:
                    res = await client.get(quote_url, headers=headers, params=params)
                    if res.status_code == 200:
                        payload = res.json()
                        data = payload.get("data", [])
                        if isinstance(data, dict):
                            data = [data]

                        for item in data:
                            sec_id = str(item.get("security_id") or "")
                            ltp = item.get("last_price") or item.get("last_traded_price") or item.get("ltp")
                            vwap = item.get("avg_price") or ltp

                            if ltp is not None:
                                ltp_val = float(ltp)
                                vwap_val = float(vwap) if vwap else ltp_val

                                if sec_id == "13":
                                    live_market_cache["NIFTY"]["ltp"] = ltp_val
                                    live_market_cache["NIFTY"]["vwap"] = vwap_val
                                    logger.info(f"NIFTY 50 Live: {ltp_val}")
                                elif sec_id == "25":
                                    live_market_cache["BANKNIFTY"]["ltp"] = ltp_val
                                    live_market_cache["BANKNIFTY"]["vwap"] = vwap_val
                                elif sec_id == "2885":
                                    live_market_cache["RELIANCE"]["ltp"] = ltp_val
                                elif sec_id == "1333":
                                    live_market_cache["HDFCBANK"]["ltp"] = ltp_val
                    else:
                        logger.warning(f"Paytm API Response [{res.status_code}]: {res.text}")
                except Exception as exc:
                    logger.error(f"Quote Polling Exception: {exc}")

            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_paytm_live_quotes())


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
