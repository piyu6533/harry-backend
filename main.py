from fastapi.responses import RedirectResponse, HTMLResponse

# ૧. સીધું એક ક્લિકમાં પેટીએમ લૉગિન પેજ ખોલવા માટે
@app.get("/login")
def login_redirect():
    login_url = f"https://login.paytmmoney.com/merchant-login?apiKey={API_KEY}"
    return RedirectResponse(login_url)

# ૨. લૉગિન થયા પછી પેટીએમ અહીં પાછું આવશે અને આપોઆપ ટોકન બતાવશે
@app.get("/callback")
async def paytm_callback(requestToken: str = ""):
    if not requestToken:
        return HTMLResponse("<h3 style='color:red;'>Request Token Not Found!</h3>")
    
    # Request Token પરથી Access Token જનરેટ કરવા માટે પેટીએમને કોલ
    async with httpx.AsyncClient() as client:
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
            global ACCESS_TOKEN
            ACCESS_TOKEN = token
            return HTMLResponse(f"""
                <body style="background:#080b11; color:#00dc82; font-family:sans-serif; text-align:center; padding-top:50px;">
                    <h2>✅ LIVE FEED ACTIVATED!</h2>
                    <p style="color:#94a3b8;">Paytm Money Access Token successfully generated and loaded into backend.</p>
                    <a href="https://piyu6533.github.io/harry-nifty-app/" style="background:#06b6d4; color:#000; padding:10px 20px; text-decoration:none; font-weight:bold; border-radius:5px;">Open Trading Terminal</a>
                </body>
            """)
        else:
            return HTMLResponse(f"<h3 style='color:red;'>Failed to generate token: {data}</h3>")
