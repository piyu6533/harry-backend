import asyncio
import json
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
import uvicorn

app = FastAPI(title="harry-nifty Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "b29e5048f9ab47bc9ff6a33f4d1fceb9"
API_SECRET = "17fce6cce6ca45548ba54db681d8846c"
ACCESS_TOKEN = ""

clients = set()

live_market_cache = {
    "NIFTY": {"ltp": 24380.40, "vwap": 24320.00, "pcr": 1.24},
    "BANKNIFTY": {"ltp": 51840.10, "vwap": 51950.00, "pcr": 0.86},
    "SENSEX": {"ltp": 80120.50, "vwap": 79950.00, "pcr": 1.30},
    "FINNIFTY": {"ltp": 23910.80, "vwap": 23890.00, "pcr": 1.08},
    "RELIANCE": {"ltp": 2890.50, "vwap": 2872.00, "pcr": 1.31},
    "HDFCBANK": {"ltp": 1682.20, "vwap": 1690.00, "pcr": 0.82}
}

@app.get("/")
def root():
    return {
        "status": "online",
        "access_token_active": bool(ACCESS_TOKEN),
        "feed_mode": "REAL_PAYTM_STREAM" if ACCESS_TOKEN else "WAITING_TOKEN"
    }

# ૧. સીધા ૧-ક્લિક લૉગિન માટે
@app.get("/login")
def login_redirect():
    login_url = f"https://login.paytmmoney.com/merchant-login?apiKey={API_KEY}"
    return RedirectResponse(login_url)

# ૨. પેટીએમ અહીં પાછું આવીને ઓટોમેટિક Access Token બનાવશે
@app.get("/callback")
async def paytm_callback(requestToken: str = ""):
    global ACCESS_TOKEN
    if not requestToken:
        return HTMLResponse("<h3 style='color:red;'>Error: requestToken not received from Paytm</h3>")
    
    # Request Token ને Access Token માં બદલો
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_res = await client.post(
                "https://developer.paytmmoney.com/accounts/v2/gettoken",
                json={
                    "api_key": API_KEY,
                    "api_secret_key": API_SECRET,
                    "request_token": requestToken
                }
            )
            data = token_res.json()
            token = data.get("data", {}).get("access_token") or data.get("access_token")
            
            if token:
                ACCESS_TOKEN = token
                return HTMLResponse("""
                    <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:60px;">
                        <h2 style="font-size:26px;">✅ LIVE FEED ACTIVATED!</h2>
                        <p style="color:#94a3b8; margin-bottom:25px;">Paytm Money Access Token successfully generated and loaded into backend.</p>
                        <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:12px 24px; text-decoration:none; font-weight:bold; border-radius:6px; font-size:14px;">Open Trading Terminal</a>
                    </body>
                """)
            else:
                return HTMLResponse(f"<h3 style='color:red;'>Token Generation Failed: {data}</h3>")
        except Exception as e:
            return HTMLResponse(f"<h3 style='color:red;'>Exception: {str(e)}</h3>")

# મેન્યુઅલ ટોકન સેટ કરવા માટે
@app.get("/set-token")
def set_token(token: str):
    global ACCESS_TOKEN
    ACCESS_TOKEN = token.strip()
    return {"message": "Access Token updated successfully", "status": "LIVE"}

# Real Market Quote Streamer
async def fetch_paytm_live_quotes():
    headers = {
        "x-api-key": API_KEY,
        "x-jwt-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=3.0) as client:
        while True:
            if ACCESS_TOKEN:
                try:
                    params = {"pref": "NSE:NIFTY 50,NSE:NIFTY BANK,NSE:RELIANCE,NSE:HDFCBANK"}
                    response = await client.get(
                        "https://developer.paytmmoney.com/data/v1/quotes/live",
                        headers={"x-api-key": API_KEY, "x-jwt-token": ACCESS_TOKEN},
                        params=params
                    )
                    if response.status_code == 200:
                        res_data = response.json().get("data", [])
                        for item in res_data:
                            sym = item.get("symbol")
                            ltp = item.get("last_price")
                            if sym in live_market_cache and ltp:
                                live_market_cache[sym]["ltp"] = float(ltp)
                                live_market_cache[sym]["vwap"] = float(item.get("avg_price", ltp))
                except Exception as e:
                    pass
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_paytm_live_quotes())

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.send_text(json.dumps({
                "type": "TICK_UPDATE",
                "data": live_market_cache
            }))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
