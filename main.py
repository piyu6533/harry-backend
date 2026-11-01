import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="harry-nifty Cloud Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "c43893b664864a618a754e190f6fd922"
API_SECRET = "ed00240b305d4ecfb28cd911bcdaf7cb"

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
    return {"status": "running_24x7", "broker": "Paytm Money"}

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