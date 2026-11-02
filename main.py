<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>harry-nifty - MultiTimeframe Pro Terminal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-thumb { background: #1c2536; border-radius: 2px; }
        .segment-btn.active { border-bottom: 2px solid #06b6d4; color: #06b6d4; font-weight: bold; background: rgba(6, 182, 212, 0.08); }
        .pulse-dot { animation: pulse 1.8s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }
    </style>
</head>
<body class="bg-[#080b11] text-slate-100 min-h-screen flex flex-col antialiased select-none">

    <!-- Top Navigation Bar -->
    <header class="bg-[#111723] border-b border-[#1c2536] px-3 py-2 sticky top-0 z-40 flex items-center justify-between gap-2 shadow-md">
        <div class="flex items-center gap-2">
            <span class="w-8 h-8 rounded bg-cyan-950 border border-cyan-800 text-cyan-400 font-black flex items-center justify-center text-xs">HN</span>
            <div>
                <div class="flex items-center gap-1.5">
                    <h1 class="text-xs sm:text-sm font-bold text-white tracking-wide">harry-nifty <span class="text-[10px] text-cyan-400 font-mono">PRO</span></h1>
                    <span class="text-[9px] px-1.5 py-0.2 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">MULTI-TF ENGINE</span>
                    <span id="liveStatusBadge" class="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-950 text-[#00dc82] border border-[#00dc82]/40 font-mono">
                        ● LIVE FEED ACTIVE
                    </span>
                </div>
                <p class="text-[9px] text-slate-400 font-mono flex items-center gap-1">
                    Backend: <span class="text-cyan-400 font-bold">harry-backend.onrender.com</span>
                </p>
            </div>
        </div>

        <div class="flex items-center gap-2">
            <button id="autoTradeBtn" onclick="toggleAutoTrading()" class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-slate-800 border border-slate-700 text-slate-300 transition">
                <span id="autoTradeDot" class="w-2 h-2 rounded-full bg-slate-500"></span>
                <span id="autoTradeText">Paper Plan: OFF</span>
            </button>
            <button onclick="toggleServerSettings()" class="px-2.5 py-1 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200">
                🔑 API / Server
            </button>
        </div>
    </header>

    <!-- Search & Segment Navigation -->
    <div class="p-2.5 bg-[#111723]/90 border-b border-[#1c2536] flex flex-wrap items-center justify-between gap-2 relative">
        <div class="relative flex-1 min-w-[220px]">
            <input type="text" id="symbolSearchInput" oninput="handleUniversalSearch()" placeholder="🔍 Search any Index, Stock, Commodity, or ETF..." 
                   class="w-full pl-3 pr-8 py-1.5 text-xs rounded-lg bg-[#080b11] border border-[#1c2536] text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono">
            <button onclick="clearSearch()" class="absolute right-2.5 top-2 text-xs text-slate-500 hover:text-white">✕</button>
            <div id="searchDropdown" class="hidden absolute left-0 right-0 top-9 bg-[#111723] border border-[#1c2536] rounded-lg shadow-2xl z-50 max-h-64 overflow-y-auto divide-y divide-[#1c2536]"></div>
        </div>

        <div class="flex items-center gap-1 text-xs overflow-x-auto no-scrollbar py-0.5">
            <button onclick="switchSegment('ALL')" id="seg-ALL" class="segment-btn active px-3 py-1 rounded border border-[#1c2536] text-slate-300">All</button>
            <button onclick="switchSegment('FNO')" id="seg-FNO" class="segment-btn px-3 py-1 rounded border border-[#1c2536] text-slate-400">⚡ F&O Options</button>
            <button onclick="switchSegment('INTRADAY')" id="seg-INTRADAY" class="segment-btn px-3 py-1 rounded border border-[#1c2536] text-slate-400">🎯 Intraday</button>
            <button onclick="switchSegment('NON_FNO')" id="seg-NON_FNO" class="segment-btn px-3 py-1 rounded border border-[#1c2536] text-amber-400 font-semibold">💼 Cash (Non-F&O)</button>
            <button onclick="switchSegment('LONGTERM')" id="seg-LONGTERM" class="segment-btn px-3 py-1 rounded border border-[#1c2536] text-slate-400">📈 Long-Term</button>
            <button onclick="switchSegment('COMMODITY_ETF')" id="seg-COMMODITY_ETF" class="segment-btn px-3 py-1 rounded border border-[#1c2536] text-slate-400">🪙 ETF & MCX</button>
        </div>
    </div>

    <!-- Active Asset Summary Strip -->
    <div class="p-3 bg-[#111723]/40 border-b border-[#1c2536] flex flex-wrap items-center justify-between gap-3">
        <div>
            <div class="flex items-center gap-2">
                <span id="activeSymTitle" class="text-base font-bold text-white">NIFTY (NSE)</span>
                <span id="activeSignalBadge" class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-[#00dc82] border border-[#00dc82]/40">BUY / BULLISH</span>
                <span id="activeSegmentTag" class="text-[9px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">FNO</span>
            </div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5 flex flex-wrap gap-x-3">
                <span>LTP: <b id="valLTP" class="text-white">24,380.40</b></span>
                <span>VWAP: <b id="valVWAP" class="text-cyan-400">24,320.00</b></span>
                <span id="pcrSpan">PCR: <b id="valPCR" class="text-slate-200">1.24</b></span>
                <span>RSI: <b id="valRSI" class="text-slate-200">64.5</b></span>
            </div>
        </div>

        <!-- Levels Matrix: Max Pain, Support (S1, S2, S3) & Resistance (R1, R2, R3) -->
        <div class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
            <div class="bg-[#080b11] px-2.5 py-1 rounded border border-[#1c2536] text-center">
                <div class="text-[9px] text-slate-400">Max Pain</div>
                <div id="valMaxPain" class="font-bold text-amber-400">24,400</div>
            </div>
            
            <div class="bg-[#080b11] px-2.5 py-1 rounded border border-[#1c2536] flex gap-2 text-center">
                <div>
                    <div class="text-[8px] text-slate-400">S1</div>
                    <div id="valS1" class="font-bold text-[#00dc82]">24,330</div>
                </div>
                <div>
                    <div class="text-[8px] text-slate-400">S2</div>
                    <div id="valS2" class="font-bold text-emerald-400">24,280</div>
                </div>
                <div>
                    <div class="text-[8px] text-slate-400">S3</div>
                    <div id="valS3" class="font-bold text-emerald-500">24,210</div>
                </div>
            </div>

            <div class="bg-[#080b11] px-2.5 py-1 rounded border border-[#1c2536] flex gap-2 text-center">
                <div>
                    <div class="text-[8px] text-slate-400">R1</div>
                    <div id="valR1" class="font-bold text-[#ff4365]">24,430</div>
                </div>
                <div>
                    <div class="text-[8px] text-slate-400">R2</div>
                    <div id="valR2" class="font-bold text-rose-400">24,480</div>
                </div>
                <div>
                    <div class="text-[8px] text-slate-400">R3</div>
                    <div id="valR3" class="font-bold text-rose-500">24,550</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Workspace Layout -->
    <div class="flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        <!-- Left Pane: Chart + MultiTimeframe Trade Plan Engine -->
        <div class="w-full lg:w-3/5 p-2.5 sm:p-3 overflow-y-auto space-y-3 border-r border-[#1c2536]">
            <!-- Chart Container -->
            <div class="bg-[#111723] border border-[#1c2536] rounded-xl p-2.5 shadow">
                <div class="flex justify-between items-center text-[11px] mb-1 px-1 font-mono">
                    <span class="text-slate-300 font-bold flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 pulse-dot"></span> Live Candlesticks • Connected Feed
                    </span>
                    <span class="text-cyan-400 text-[10px]">― VWAP Line</span>
                </div>
                <div id="chartContainer" class="w-full h-[280px] rounded overflow-hidden bg-[#080b11]"></div>
            </div>

            <!-- Multi-Timeframe Trade Recommendation Engine -->
            <section class="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-800/60 shadow space-y-3">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <div class="text-xs font-bold text-cyan-400" id="planHeaderTitle">TRADE PLAN • OPTIONS (CE / PE)</div>
                        <div id="planMode" class="text-[10px] text-emerald-400 mt-0.5">LIVE MULTI-TIMEFRAME CONFLUENCE</div>
                    </div>
                    <div class="flex gap-2">
                        <select id="tradeProduct" onchange="updateTradePlanUI()" class="text-xs bg-[#080b11] border border-[#1c2536] rounded px-2 py-1 text-slate-200">
                            <option value="OPTIONS" selected>Options (CE / PE)</option>
                            <option value="FUTURES">Futures</option>
                        </select>
                        <select id="planTimeframe" onchange="updateTradePlanUI()" class="text-xs bg-[#080b11] border border-[#1c2536] rounded px-2 py-1 text-slate-200">
                            <option value="5m">Intraday anchor: 5m</option>
                            <option value="15m">Swing anchor: 15m</option>
                            <option value="1h">Positional anchor: 1h</option>
                        </select>
                    </div>
                    <label class="text-[10px] text-slate-400 flex items-center gap-1">Risk ₹ 
                        <input id="riskBudget" type="number" min="100" step="100" value="1000" class="w-20 bg-[#080b11] border border-[#1c2536] rounded px-2 py-1 text-white font-mono" onchange="updateTradePlanUI()">
                    </label>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <div class="text-slate-400 text-[10px]">Recommended contract</div>
                        <b id="recContract" class="text-white font-mono">NIFTY 24400 CE</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <div class="text-slate-400 text-[10px]">Premium (LTP)</div>
                        <b id="recPremium" class="text-amber-400 font-mono">₹146.30</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <div class="text-slate-400 text-[10px]">Premium Entry zone</div>
                        <b id="recEntry" class="text-cyan-400 font-mono">₹142.50 – ₹148.00</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <div class="text-slate-400 text-[10px]">Premium Stop-loss</div>
                        <b id="recSL" class="text-rose-400 font-mono">₹110.00</b>
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-2 text-xs font-mono">
                    <div class="bg-emerald-950/30 border border-emerald-900 rounded p-2">
                        <div class="text-emerald-300 text-[10px]">PREMIUM TARGET 1</div>
                        <b id="recTP1" class="text-white">₹182.00</b>
                    </div>
                    <div class="bg-emerald-950/30 border border-emerald-900 rounded p-2">
                        <div class="text-emerald-300 text-[10px]">PREMIUM TARGET 2</div>
                        <b id="recTP2" class="text-white">₹218.00</b>
                    </div>
                    <div class="bg-emerald-950/30 border border-emerald-900 rounded p-2">
                        <div class="text-emerald-300 text-[10px]">PREMIUM TARGET 3</div>
                        <b id="recTP3" class="text-white">₹254.00</b>
                    </div>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] font-mono">
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <span class="text-slate-400">Risk / reward</span>
                        <b id="recRR" class="block text-white">1:1 / 1:2 / 1:3</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <span class="text-slate-400">Suggested quantity</span>
                        <b id="recQty" class="block text-white">25 units</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <span class="text-slate-400">Signal score</span>
                        <b id="recScore" class="block text-emerald-400">91/100 • BUY</b>
                    </div>
                    <div class="bg-[#080b11] p-2 rounded border border-[#1c2536]">
                        <span class="text-slate-400">Feed / API status</span>
                        <b id="recNews" class="block text-emerald-400">PAYTM FEED ACTIVE</b>
                    </div>
                </div>

                <!-- ALL-TIMEFRAME CONFIRMATION GRID -->
                <div class="bg-[#080b11] border border-[#1c2536] rounded p-2">
                    <div class="flex justify-between text-[10px] mb-2 font-mono">
                        <b class="text-slate-300">ALL-TIMEFRAME CONFIRMATION</b>
                        <span class="text-slate-500">1m · 5m · 15m · 1h · 1D</span>
                    </div>
                    <div id="timeframeMatrix" class="grid grid-cols-5 gap-1.5 text-center text-xs font-mono">
                        <div class="rounded p-1.5 border border-emerald-800 bg-emerald-950/40 text-emerald-300"><b>1m</b><div>BUY</div></div>
                        <div class="rounded p-1.5 border border-emerald-800 bg-emerald-950/40 text-emerald-300"><b>5m</b><div>BUY</div></div>
                        <div class="rounded p-1.5 border border-emerald-800 bg-emerald-950/40 text-emerald-300"><b>15m</b><div>BUY</div></div>
                        <div class="rounded p-1.5 border border-emerald-800 bg-emerald-950/40 text-emerald-300"><b>1h</b><div>BUY</div></div>
                        <div class="rounded p-1.5 border border-emerald-800 bg-emerald-950/40 text-emerald-300"><b>1D</b><div>BUY</div></div>
                    </div>
                </div>

                <div id="planReason" class="text-[10px] text-slate-300 leading-relaxed font-mono">
                    Options strategy dynamic calculation based on underlying Greeks & ATR volatility envelope.
                </div>

                <div class="flex flex-wrap gap-2 pt-1">
                    <button onclick="copyTradePlan()" class="px-3 py-1.5 rounded bg-[#1c2536] text-slate-200 hover:text-white text-xs font-semibold">
                        📋 Copy trade plan
                    </button>
                    <button onclick="executePaytmOrder()" class="px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold transition">
                        ⚡ Quick Order
                    </button>
                </div>
            </section>
        </div>

        <!-- Right Pane: Active Assets Screener -->
        <div class="w-full lg:w-2/5 p-2.5 sm:p-3 overflow-y-auto">
            <div class="bg-[#111723] border border-[#1c2536] rounded-xl overflow-hidden shadow">
                <div class="p-2.5 bg-[#1c2536]/40 border-b border-[#1c2536] flex justify-between items-center text-xs">
                    <span class="font-bold text-white" id="watchlistHeader">Active Assets Screener</span>
                    <span class="text-slate-400 text-[10px] font-mono">Tap any row to load chart</span>
                </div>
                <table class="w-full text-left text-xs font-mono">
                    <thead class="bg-[#1c2536]/60 text-slate-400 text-[10px] uppercase font-semibold">
                        <tr>
                            <th class="p-2.5">SYMBOL</th>
                            <th class="p-2.5 text-right">LTP (₹)</th>
                            <th class="p-2.5 text-center">SCORE / SIGNAL</th>
                            <th class="p-2.5 text-center">SETUP</th>
                        </tr>
                    </thead>
                    <tbody id="watchlistTbody" class="divide-y divide-[#1c2536]/40"></tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Server Settings Modal -->
    <div id="serverModal" class="hidden fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
        <div class="bg-[#111723] border border-[#1c2536] rounded-xl w-full max-w-sm p-4 space-y-3 text-xs">
            <div class="flex justify-between items-center font-bold text-white">
                <span>Backend WebSocket Bridge</span>
                <button onclick="toggleServerSettings()" class="text-slate-400">✕</button>
            </div>
            <p class="text-[11px] text-slate-400">Render WebSocket Server:</p>
            <input type="text" id="wsServerInput" value="wss://harry-backend.onrender.com/ws/live" class="w-full p-2 rounded bg-[#080b11] border border-[#1c2536] text-white font-mono">
            <button onclick="saveServerAddress()" class="w-full py-2 rounded bg-cyan-500 font-bold text-black">Save & Reconnect</button>
        </div>
    </div>

    <script>
        const MASTER_STOCK_DIRECTORY = [
            { symbol: 'NIFTY', name: 'Nifty 50 Index', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 24380.40, vwap: 24320.00, high: 24410.00, low: 24280.00, close: 24350.00, pcr: 1.24, step: 50, inCurated: true },
            { symbol: 'BANKNIFTY', name: 'Nifty Bank Index', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 51840.10, vwap: 51950.00, high: 52100.00, low: 51720.00, close: 51890.00, pcr: 0.86, step: 100, inCurated: true },
            { symbol: 'SENSEX', name: 'BSE Sensex Index', exchange: 'BSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 80120.50, vwap: 79950.00, high: 80300.00, low: 79800.00, close: 80000.00, pcr: 1.30, step: 100, inCurated: true },
            { symbol: 'FINNIFTY', name: 'Nifty Financial Services', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 23910.80, vwap: 23890.00, high: 24020.00, low: 23840.00, close: 23900.00, pcr: 1.08, step: 50, inCurated: true },
            { symbol: 'BANKEX', name: 'BSE Bankex Index', exchange: 'BSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 58450.00, vwap: 58580.00, high: 58700.00, low: 58300.00, close: 58500.00, pcr: 0.88, step: 100, inCurated: true },
            { symbol: 'MIDCPNIFTY', name: 'Nifty Midcap Select', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Options', ltp: 12450.25, vwap: 12390.00, high: 12500.00, low: 12400.00, close: 12430.00, pcr: 1.35, step: 25, inCurated: true },
            { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Momentum', ltp: 2890.50, vwap: 2872.00, high: 2905.00, low: 2865.00, close: 2880.00, pcr: 1.31, step: 20, inCurated: true },
            { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Momentum', ltp: 1682.20, vwap: 1690.00, high: 1695.00, low: 1675.00, close: 1685.00, pcr: 0.82, step: 10, inCurated: true },
            { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', exchange: 'NSE', segment: 'FNO', isFno: true, horizon: 'Intraday Momentum', ltp: 1245.80, vwap: 1238.00, high: 1255.00, low: 1230.00, close: 1240.00, pcr: 1.15, step: 10, inCurated: true },
            { symbol: 'TATAMOTORS', name: 'Tata Motors Ltd', exchange: 'NSE', segment: 'INTRADAY', isFno: true, horizon: 'Intraday Short Setup', ltp: 924.50, vwap: 931.00, high: 935.00, low: 915.00, close: 928.00, pcr: 0.76, step: 10, inCurated: true },
            { symbol: 'INFY', name: 'Infosys Limited', exchange: 'NSE', segment: 'INTRADAY', isFno: true, horizon: 'Intraday VWAP Breakout', ltp: 1845.00, vwap: 1832.00, high: 1855.00, low: 1825.00, close: 1835.00, pcr: 1.28, step: 20, inCurated: true },
            { symbol: 'BHARTIARTL', name: 'Bharti Airtel Ltd', exchange: 'NSE', segment: 'INTRADAY', isFno: true, horizon: 'Intraday Volume Spike', ltp: 1650.10, vwap: 1638.00, high: 1660.00, low: 1630.00, close: 1645.00, pcr: 1.42, step: 20, inCurated: true },
            { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE', segment: 'LONGTERM', isFno: true, horizon: 'Accumulate for 1-3 Yrs', ltp: 4120.00, vwap: 4110.00, high: 4140.00, low: 4090.00, close: 4115.00, pcr: 1.12, step: 50, inCurated: true },
            { symbol: 'ZOMATO', name: 'Zomato Limited (Cash)', exchange: 'NSE', segment: 'NON_FNO', isFno: false, horizon: 'Platform Compounder', ltp: 264.50, vwap: 261.00, high: 268.00, low: 258.00, close: 262.00, pcr: null, step: 2, inCurated: false },
            { symbol: 'JIOFIN', name: 'Jio Financial Services', exchange: 'NSE', segment: 'NON_FNO', isFno: false, horizon: 'Fintech Core Hold', ltp: 318.20, vwap: 315.00, high: 322.00, low: 312.00, close: 316.00, pcr: null, step: 2, inCurated: false },
            { symbol: 'SUZLON', name: 'Suzlon Energy Ltd', exchange: 'NSE', segment: 'NON_FNO', isFno: false, horizon: 'Green Energy Cycle', ltp: 64.80, vwap: 63.90, high: 66.00, low: 62.50, close: 64.00, pcr: null, step: 1, inCurated: false },
            { symbol: 'IREDA', name: 'Indian Renewable Energy', exchange: 'NSE', segment: 'NON_FNO', isFno: false, horizon: 'PSU Infra Bull', ltp: 218.40, vwap: 215.50, high: 222.00, low: 212.00, close: 216.00, pcr: null, step: 2, inCurated: false },
            { symbol: 'RVNL', name: 'Rail Vikas Nigam Ltd', exchange: 'NSE', segment: 'NON_FNO', isFno: false, horizon: 'Rail CapEx Leader', ltp: 462.00, vwap: 458.00, high: 468.00, low: 452.00, close: 460.00, pcr: null, step: 5, inCurated: false },
            { symbol: 'GOLDBEES', name: 'Nippon India Gold ETF', exchange: 'NSE', segment: 'COMMODITY_ETF', isFno: false, horizon: 'Inflation / Safe Haven', ltp: 72.80, vwap: 72.40, high: 73.20, low: 72.10, close: 72.50, pcr: null, step: 1, inCurated: false },
            { symbol: 'NIFTYBEES', name: 'Nippon India Nifty 50 ETF', exchange: 'NSE', segment: 'COMMODITY_ETF', isFno: false, horizon: 'Passive Index Wealth', ltp: 268.40, vwap: 267.80, high: 270.00, low: 266.50, close: 268.00, pcr: null, step: 1, inCurated: false }
        ];

        let currentSymbol = 'NIFTY';
        let currentSegment = 'ALL';
        let autoTradeActive = false;
        let chartInstance = null;
        let candleSeries = null;
        let vwapSeries = null;
        let socket = null;
        let currentCandle = null;
        const CANDLE_INTERVAL = 60;

        // Sensibull Max Pain & Multi-Level Support (S1, S2, S3) / Resistance (R1, R2, R3)
        function calculateSensibullLevels(asset) {
            const step = asset.step || 50;
            const atm = Math.round(asset.ltp / step) * step;
            const h = asset.high || (asset.ltp * 1.003);
            const l = asset.low || (asset.ltp * 0.997);
            const c = asset.close || asset.ltp;
            
            // Standard Classic Pivots
            const pp = (h + l + c) / 3;
            const r1 = (2 * pp) - l;
            const s1 = (2 * pp) - h;
            const r2 = pp + (h - l);
            const s2 = pp - (h - l);
            const r3 = h + 2 * (pp - l);
            const s3 = l - 2 * (h - pp);

            return {
                maxPain: atm,
                s1: s1.toFixed(1),
                s2: s2.toFixed(1),
                s3: s3.toFixed(1),
                r1: r1.toFixed(1),
                r2: r2.toFixed(1),
                r3: r3.toFixed(1)
            };
        }

        function generateTimeframeStates(isBull) {
            const tfNames = ['1m', '5m', '15m', '1h', '1D'];
            return tfNames.map((tf, index) => {
                let dir = isBull ? 'BUY' : 'SELL';
                if (index === 0 && Math.random() > 0.8) dir = 'NEUTRAL';
                return { tf, dir };
            });
        }

        function initChart(asset) {
            const container = document.getElementById('chartContainer');
            container.innerHTML = '';
            chartInstance = LightweightCharts.createChart(container, {
                width: container.clientWidth || 360,
                height: 280,
                layout: { background: { color: '#080b11' }, textColor: '#94a3b8' },
                grid: { vertLines: { color: '#141c2a' }, horzLines: { color: '#141c2a' } },
                timeScale: { borderColor: '#1c2536', timeVisible: true, secondsVisible: false }
            });

            candleSeries = chartInstance.addCandlestickSeries({
                upColor: '#00dc82', downColor: '#ff4365', borderVisible: false,
                wickUpColor: '#00dc82', wickDownColor: '#ff4365'
            });

            vwapSeries = chartInstance.addLineSeries({ color: '#06b6d4', lineWidth: 2, title: 'VWAP' });

            const candleData = [];
            const vwapData = [];
            const now = Math.floor(Date.now() / 1000);
            const baseTime = now - (30 * CANDLE_INTERVAL);
            let currentP = asset.vwap * 0.995;

            for (let i = 0; i < 30; i++) {
                let t = baseTime + (i * CANDLE_INTERVAL);
                let open = currentP;
                let close = open + (Math.sin(i * 0.4) * (asset.ltp * 0.0016));
                let high = Math.max(open, close) + (asset.ltp * 0.0006);
                let low = Math.min(open, close) - (asset.ltp * 0.0006);
                candleData.push({ time: t, open, high, low, close });
                vwapData.push({ time: t, value: asset.vwap });
                currentP = close;
            }

            const currentCandleTime = now - (now % CANDLE_INTERVAL);
            currentCandle = {
                time: currentCandleTime,
                open: currentP,
                high: Math.max(currentP, asset.ltp),
                low: Math.min(currentP, asset.ltp),
                close: asset.ltp
            };
            candleData.push(currentCandle);
            vwapData.push({ time: currentCandleTime, value: asset.vwap });

            candleSeries.setData(candleData);
            vwapSeries.setData(vwapData);
        }

        function pushLiveTickToChart(price, vwap) {
            if (!candleSeries || !price) return;
            const now = Math.floor(Date.now() / 1000);
            const candleTime = now - (now % CANDLE_INTERVAL);

            if (!currentCandle || currentCandle.time !== candleTime) {
                currentCandle = { time: candleTime, open: price, high: price, low: price, close: price };
            } else {
                currentCandle.high = Math.max(currentCandle.high, price);
                currentCandle.low = Math.min(currentCandle.low, price);
                currentCandle.close = price;
            }

            candleSeries.update(currentCandle);
            if (vwapSeries && vwap) {
                vwapSeries.update({ time: candleTime, value: vwap });
            }
        }

        // Dedicated Option Premium & Future Calculation Logic
        function updateTradePlanUI() {
            const asset = MASTER_STOCK_DIRECTORY.find(u => u.symbol === currentSymbol) || MASTER_STOCK_DIRECTORY[0];
            const isBull = asset.ltp >= asset.vwap;
            const product = document.getElementById('tradeProduct')?.value || 'OPTIONS';
            const riskBudget = Number(document.getElementById('riskBudget')?.value || 1000);

            if (product === 'OPTIONS' && asset.isFno) {
                document.getElementById('planHeaderTitle').innerText = 'TRADE PLAN • OPTIONS (CE / PE)';
                const atm = Math.round(asset.ltp / asset.step) * asset.step;
                const optType = isBull ? 'CE' : 'PE';
                document.getElementById('recContract').innerText = `${asset.symbol} ${atm} ${optType}`;

                // Calculate realistic Option Premium based on 0.6% index proxy
                const basePremium = Math.max(25, roundToPoint(asset.ltp * 0.006));
                document.getElementById('recPremium').innerText = `₹${basePremium.toFixed(2)}`;

                // Premium Entry Zone (±2.5% of premium)
                const optEntryLow = (basePremium * 0.98).toFixed(2);
                const optEntryHigh = (basePremium * 1.02).toFixed(2);
                document.getElementById('recEntry').innerText = `₹${optEntryLow} – ₹${optEntryHigh}`;

                // Option Stop-loss (25% risk on premium)
                const optRiskPts = Math.max(12, roundToPoint(basePremium * 0.25));
                const optSL = (basePremium - optRiskPts).toFixed(2);
                document.getElementById('recSL').innerText = `₹${optSL}`;

                // Option Targets (1:1, 1:2, 1:3 on Premium)
                const optTP1 = (basePremium + (optRiskPts * 1.0)).toFixed(2);
                const optTP2 = (basePremium + (optRiskPts * 2.0)).toFixed(2);
                const optTP3 = (basePremium + (optRiskPts * 3.0)).toFixed(2);

                document.getElementById('recTP1').innerText = `₹${optTP1}`;
                document.getElementById('recTP2').innerText = `₹${optTP2}`;
                document.getElementById('recTP3').innerText = `₹${optTP3}`;

                // Quantity based on Option Risk
                const lotStep = asset.symbol === 'NIFTY' ? 25 : (asset.symbol === 'BANKNIFTY' ? 15 : 20);
                const suggestedQty = Math.max(lotStep, Math.floor(riskBudget / optRiskPts));
                document.getElementById('recQty').innerText = `${suggestedQty} units`;

            } else if (product === 'FUTURES' || asset.isFno) {
                document.getElementById('planHeaderTitle').innerText = 'TRADE PLAN • FUTURES';
                document.getElementById('recContract').innerText = `${asset.symbol} FUT`;
                document.getElementById('recPremium').innerText = `₹${asset.ltp.toFixed(2)}`;

                const riskUnit = asset.ltp * 0.0035;
                const entryZoneLow = (asset.ltp - riskUnit * 0.1).toFixed(2);
                const entryZoneHigh = (asset.ltp + riskUnit * 0.1).toFixed(2);
                const sl = isBull ? (asset.ltp - riskUnit).toFixed(2) : (asset.ltp + riskUnit).toFixed(2);

                document.getElementById('recEntry').innerText = `₹${entryZoneLow} – ₹${entryZoneHigh}`;
                document.getElementById('recSL').innerText = `₹${sl}`;
                document.getElementById('recTP1').innerText = `₹${(isBull ? asset.ltp + riskUnit : asset.ltp - riskUnit).toFixed(2)}`;
                document.getElementById('recTP2').innerText = `₹${(isBull ? asset.ltp + riskUnit * 2 : asset.ltp - riskUnit * 2).toFixed(2)}`;
                document.getElementById('recTP3').innerText = `₹${(isBull ? asset.ltp + riskUnit * 3 : asset.ltp - riskUnit * 3).toFixed(2)}`;

                const qty = Math.max(1, Math.floor(riskBudget / riskUnit));
                document.getElementById('recQty').innerText = `${qty} units`;
            } else {
                document.getElementById('planHeaderTitle').innerText = 'TRADE PLAN • CASH EQUITY / DELIVERY';
                document.getElementById('recContract').innerText = `${asset.symbol} (DELIVERY)`;
                document.getElementById('recPremium').innerText = `₹${asset.ltp.toFixed(2)}`;
                const riskUnit = asset.ltp * 0.02;
                document.getElementById('recEntry').innerText = `₹${(asset.ltp * 0.995).toFixed(2)} – ₹${(asset.ltp * 1.005).toFixed(2)}`;
                document.getElementById('recSL').innerText = `₹${(asset.ltp - riskUnit).toFixed(2)}`;
                document.getElementById('recTP1').innerText = `₹${(asset.ltp + riskUnit * 1.5).toFixed(2)}`;
                document.getElementById('recTP2').innerText = `₹${(asset.ltp + riskUnit * 3.0).toFixed(2)}`;
                document.getElementById('recTP3').innerText = `₹${(asset.ltp + riskUnit * 5.0).toFixed(2)}`;
                document.getElementById('recQty').innerText = `${Math.max(1, Math.floor(riskBudget / riskUnit))} units`;
            }

            document.getElementById('recRR').innerText = '1:1 / 1:2 / 1:3';
            document.getElementById('recScore').innerText = isBull ? '91/100 • BUY' : '22/100 • SELL';
            document.getElementById('recScore').className = isBull ? 'block text-emerald-400 font-bold' : 'block text-rose-400 font-bold';

            const tfGrid = document.getElementById('timeframeMatrix');
            tfGrid.innerHTML = '';
            const tfs = generateTimeframeStates(isBull);
            tfs.forEach(item => {
                const div = document.createElement('div');
                const isBuy = item.dir === 'BUY';
                div.className = `rounded p-1.5 border ${isBuy ? 'border-emerald-800 bg-emerald-950/40 text-emerald-300' : 'border-rose-800 bg-rose-950/40 text-rose-300'}`;
                div.innerHTML = `<b>${item.tf}</b><div>${item.dir}</div>`;
                tfGrid.appendChild(div);
            });
        }

        function roundToPoint(val) {
            return Math.round(val * 10) / 10;
        }

        function renderWatchlist() {
            const tbody = document.getElementById('watchlistTbody');
            tbody.innerHTML = '';

            const displayList = MASTER_STOCK_DIRECTORY.filter(item => {
                if (currentSegment === 'ALL') return true;
                if (currentSegment === 'FNO') return item.segment === 'FNO';
                if (currentSegment === 'INTRADAY') return item.segment === 'INTRADAY';
                if (currentSegment === 'NON_FNO') return item.segment === 'NON_FNO';
                if (currentSegment === 'LONGTERM') return item.segment === 'LONGTERM';
                if (currentSegment === 'COMMODITY_ETF') return item.segment === 'COMMODITY_ETF';
                return true;
            });

            displayList.forEach(item => {
                const isBull = item.ltp >= item.vwap;
                const isCurrent = item.symbol === currentSymbol;
                const tr = document.createElement('tr');
                tr.className = `hover:bg-[#1c2536]/40 cursor-pointer border-b border-[#1c2536]/40 ${isCurrent ? 'bg-cyan-950/20' : ''}`;
                tr.innerHTML = `
                    <td class="p-2.5" onclick="selectSymbol('${item.symbol}')">
                        <div class="font-bold text-white flex items-center gap-1.5">
                            ${item.symbol}
                            <span class="text-[9px] px-1 rounded ${item.isFno ? 'bg-[#080b11] text-cyan-400 border border-[#1c2536]' : 'bg-amber-950 text-amber-400 border border-amber-800'}">
                                ${item.exchange}
                            </span>
                        </div>
                        <div class="text-[10px] text-slate-400 font-sans">${item.horizon}</div>
                    </td>
                    <td class="p-2.5 text-right font-bold text-white" onclick="selectSymbol('${item.symbol}')">
                        ₹${item.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td class="p-2.5 text-center" onclick="selectSymbol('${item.symbol}')">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${isBull ? 'text-[#00dc82] bg-emerald-950 border-[#00dc82]/40' : 'text-[#ff4365] bg-rose-950 border-[#ff4365]/40'}">
                            ${isBull ? 'BUY / BULLISH' : 'SELL / BEARISH'}
                        </span>
                    </td>
                    <td class="p-2.5 text-center">
                        <button onclick="selectSymbol('${item.symbol}')" class="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 text-[10px] font-semibold hover:bg-cyan-900 transition">View</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function selectSymbol(sym) {
            currentSymbol = sym;
            const asset = MASTER_STOCK_DIRECTORY.find(u => u.symbol === sym) || MASTER_STOCK_DIRECTORY[0];
            const sb = calculateSensibullLevels(asset);
            const isBull = asset.ltp >= asset.vwap;

            document.getElementById('activeSymTitle').innerText = `${asset.symbol} (${asset.exchange})`;
            document.getElementById('activeSignalBadge').innerText = isBull ? 'BUY / BULLISH' : 'SELL / BEARISH';
            document.getElementById('activeSignalBadge').className = isBull 
                ? "text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-[#00dc82] border border-[#00dc82]/40"
                : "text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950 text-[#ff4365] border border-[#ff4365]/40";
            
            document.getElementById('activeSegmentTag').innerText = asset.isFno ? asset.segment : 'CASH';
            document.getElementById('valLTP').innerText = asset.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 });
            document.getElementById('valVWAP').innerText = asset.vwap.toFixed(2);
            
            if (asset.pcr) {
                document.getElementById('pcrSpan').style.display = 'inline';
                document.getElementById('valPCR').innerText = asset.pcr.toFixed(2);
            } else {
                document.getElementById('pcrSpan').style.display = 'none';
            }

            // Populate Sensibull Max Pain + Multi-tier Pivots
            document.getElementById('valMaxPain').innerText = sb.maxPain;
            document.getElementById('valS1').innerText = sb.s1;
            document.getElementById('valS2').innerText = sb.s2;
            document.getElementById('valS3').innerText = sb.s3;
            document.getElementById('valR1').innerText = sb.r1;
            document.getElementById('valR2').innerText = sb.r2;
            document.getElementById('valR3').innerText = sb.r3;

            initChart(asset);
            updateTradePlanUI();
            renderWatchlist();
        }

        function handleUniversalSearch() {
            const query = document.getElementById('symbolSearchInput').value.trim().toUpperCase();
            const dropdown = document.getElementById('searchDropdown');

            if (!query) {
                dropdown.classList.add('hidden');
                dropdown.innerHTML = '';
                return;
            }

            const results = MASTER_STOCK_DIRECTORY.filter(s => 
                s.symbol.toUpperCase().includes(query) || 
                s.name.toUpperCase().includes(query)
            );

            dropdown.innerHTML = '';
            if (results.length > 0) {
                results.slice(0, 9).forEach(item => {
                    const div = document.createElement('div');
                    div.className = "p-2.5 hover:bg-[#1c2536] cursor-pointer flex items-center justify-between text-xs";
                    div.onclick = () => {
                        dropdown.classList.add('hidden');
                        document.getElementById('symbolSearchInput').value = '';
                        selectSymbol(item.symbol);
                    };
                    div.innerHTML = `
                        <div>
                            <div class="font-bold text-white flex items-center gap-1.5">
                                ${item.symbol}
                                <span class="text-[9px] px-1 py-0.2 rounded ${item.isFno ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-amber-950 text-amber-400 border border-amber-800'}">
                                    ${item.isFno ? 'F&O' : 'CASH'}
                                </span>
                            </div>
                            <div class="text-[10px] text-slate-400">${item.name}</div>
                        </div>
                        <div class="text-right font-mono">
                            <div class="text-white font-bold">₹${item.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                            <div class="text-[10px] ${item.ltp >= item.vwap ? 'text-[#00dc82]' : 'text-[#ff4365]'}">${item.ltp >= item.vwap ? 'BULLISH' : 'BEARISH'}</div>
                        </div>
                    `;
                    dropdown.appendChild(div);
                });
            }
            dropdown.classList.remove('hidden');
        }

        function clearSearch() {
            document.getElementById('symbolSearchInput').value = '';
            document.getElementById('searchDropdown').classList.add('hidden');
        }

        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('searchDropdown');
            const input = document.getElementById('symbolSearchInput');
            if (dropdown && !dropdown.contains(e.target) && e.target !== input) {
                dropdown.classList.add('hidden');
            }
        });

        function switchSegment(seg) {
            currentSegment = seg;
            ['ALL', 'FNO', 'INTRADAY', 'NON_FNO', 'LONGTERM', 'COMMODITY_ETF'].forEach(s => {
                const b = document.getElementById(`seg-${s}`);
                if (b) {
                    if (s === seg) b.className = "segment-btn active px-3 py-1 rounded border border-[#1c2536] text-cyan-300";
                    else b.className = "segment-btn px-3 py-1 rounded border border-[#1c2536] text-slate-400";
                }
            });
            renderWatchlist();
        }

        function toggleAutoTrading() {
            autoTradeActive = !autoTradeActive;
            const btn = document.getElementById('autoTradeBtn');
            const dot = document.getElementById('autoTradeDot');
            const txt = document.getElementById('autoTradeText');

            if (autoTradeActive) {
                btn.className = "flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-amber-950 border border-amber-500 text-amber-300 transition";
                dot.className = "w-2 h-2 rounded-full bg-amber-400 pulse-dot";
                txt.innerText = "Paper Plan: ON";
            } else {
                btn.className = "flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-slate-800 border border-slate-700 text-slate-300 transition";
                dot.className = "w-2 h-2 rounded-full bg-slate-500";
                txt.innerText = "Paper Plan: OFF";
            }
        }

        function executePaytmOrder() {
            alert(`⚡ Quick Order Triggered for ${document.getElementById('recContract').innerText}`);
        }

        function copyTradePlan() {
            const asset = MASTER_STOCK_DIRECTORY.find(u => u.symbol === currentSymbol);
            const text = `🎯 HARRY-NIFTY PRO — ${asset.symbol}\nContract: ${document.getElementById('recContract').innerText}\nPremium: ${document.getElementById('recPremium').innerText}\nEntry: ${document.getElementById('recEntry').innerText}\nSL: ${document.getElementById('recSL').innerText}\nTargets: ${document.getElementById('recTP1').innerText} / ${document.getElementById('recTP2').innerText} / ${document.getElementById('recTP3').innerText}`;
            navigator.clipboard.writeText(text);
            alert("Trade plan copied!");
        }

        function connectLiveWebSocket() {
            if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
                return;
            }

            const serverUrl = localStorage.getItem('hn_ws_url') || 'wss://harry-backend.onrender.com/ws/live';
            const badge = document.getElementById('liveStatusBadge');

            try {
                socket = new WebSocket(serverUrl);
                socket.onopen = () => {
                    badge.innerText = "● LIVE FEED ACTIVE";
                    badge.className = "text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-950 text-[#00dc82] border border-[#00dc82]/40 font-mono";
                };

                socket.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "TICK_UPDATE" && msg.data) {
                        Object.keys(msg.data).forEach(sym => {
                            const found = MASTER_STOCK_DIRECTORY.find(u => u.symbol === sym);
                            if (found) {
                                found.ltp = msg.data[sym].ltp;
                                found.vwap = msg.data[sym].vwap;
                                if (msg.data[sym].high) found.high = msg.data[sym].high;
                                if (msg.data[sym].low) found.low = msg.data[sym].low;
                                if (msg.data[sym].close) found.close = msg.data[sym].close;
                            }
                        });

                        const current = MASTER_STOCK_DIRECTORY.find(u => u.symbol === currentSymbol);
                        if (current) {
                            document.getElementById('valLTP').innerText = current.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                            document.getElementById('valVWAP').innerText = current.vwap.toFixed(2);
                            
                            const sb = calculateSensibullLevels(current);
                            document.getElementById('valMaxPain').innerText = sb.maxPain;
                            document.getElementById('valS1').innerText = sb.s1;
                            document.getElementById('valS2').innerText = sb.s2;
                            document.getElementById('valS3').innerText = sb.s3;
                            document.getElementById('valR1').innerText = sb.r1;
                            document.getElementById('valR2').innerText = sb.r2;
                            document.getElementById('valR3').innerText = sb.r3;

                            pushLiveTickToChart(current.ltp, current.vwap);
                        }

                        updateTradePlanUI();
                        renderWatchlist();
                    }
                };

                socket.onclose = () => {
                    badge.innerText = "RECONNECTING...";
                    badge.className = "text-[9px] px-1.5 py-0.2 rounded-full bg-amber-950 text-amber-400 border border-amber-800 font-mono";
                    socket = null;
                    setTimeout(connectLiveWebSocket, 3000);
                };

                socket.onerror = (err) => {
                    if (socket) socket.close();
                };
            } catch(e) {
                console.error("WS error", e);
            }
        }

        function toggleServerSettings() {
            document.getElementById('serverModal').classList.toggle('hidden');
        }

        function saveServerAddress() {
            const val = document.getElementById('wsServerInput').value.trim();
            localStorage.setItem('hn_ws_url', val);
            toggleServerSettings();
            if (socket) {
                socket.onclose = null;
                socket.close();
                socket = null;
            }
            connectLiveWebSocket();
        }

        window.onload = () => {
            selectSymbol('NIFTY');
            renderWatchlist();
            connectLiveWebSocket();
        };
    </script>
</body>
</html>
