import asyncio
import json
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="harry-nifty Live Paytm Data Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "c43893b664864a618a754e190f6fd922"
API_SECRET = "ed00240b305d4ecfb28cd911bcdaf7cb"

# દરરોજ સવારે Paytm Money માંથી મળતો એક્સેસ ટોકન અહીં અથવા એન્વાયરન્મેન્ટ વેરિયેબલમાં મૂકવો
ACCESS_TOKEN = ""

clients = set()

# રિયલ માર્કેટ કૅશ
live_market_cache = {
    "NIFTY": {"ltp": 24380.40, "vwap": 24320.00, "pcr": 1.24},
    "BANKNIFTY": {"ltp": 51840.10, "vwap": 51950.00, "pcr": 0.86},
    "SENSEX": {"ltp": 80120.50, "vwap": 79950.00, "pcr": 1.30},
    "FINNIFTY": {"ltp": 23910.80, "vwap": 23890.00, "pcr": 1.08},
    "RELIANCE": {"ltp": 2890.50, "vwap": 2872.00, "pcr": 1.31},
    "HDFCBANK": {"ltp": 1682.20, "vwap": 1690.00, "pcr": 0.82}
}

# Paytm Money Security ID Mapping
PAYTM_INSTRUMENT_MAP = {
    "NIFTY": {"sec_id": "NSE:NIFTY 50", "mode": "LTP"},
    "BANKNIFTY": {"sec_id": "NSE:NIFTY BANK", "mode": "LTP"},
    "SENSEX": {"sec_id": "BSE:SENSEX", "mode": "LTP"},
    "FINNIFTY": {"sec_id": "NSE:FINNIFTY", "mode": "LTP"},
    "RELIANCE": {"sec_id": "NSE:RELIANCE", "mode": "FULL"},
    "HDFCBANK": {"sec_id": "NSE:HDFCBANK", "mode": "FULL"}
}

@app.get("/")
def root():
    return {
        "status": "online",
        "feed_mode": "REAL_MARKET_STREAM" if ACCESS_TOKEN else "WAITING_ACCESS_TOKEN"
    }

# નવો Daily Token સેવ કરવા માટેનો એન્ડપોઇન્ટ
@app.post("/set-token")
def set_token(token: str):
    global ACCESS_TOKEN
    ACCESS_TOKEN = token.strip()
    return {"message": "Access Token updated successfully", "status": "LIVE"}

# Paytm Money Live Quote Poller / Streamer
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
                    # Paytm Money Real Quote API Call
                    # URL: https://developer.paytmmoney.com/data/v1/quotes/live
                    params = {"pref": "NSE:NIFTY 50,NSE:NIFTY BANK,NSE:RELIANCE,NSE:HDFCBANK"}
                    response = await client.get(
                        "https://developer.paytmmoney.com/data/v1/quotes/live",
                        headers=headers,
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
                except Exception as err:
                    print("Paytm API Stream Error:", err)

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
