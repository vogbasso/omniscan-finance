import os
import json
import time
import warnings
warnings.filterwarnings("ignore")

import requests
import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

def fmt_currency(val: float) -> str:
    if not val or val == 0:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    elif val >= 1e9:
        return f"${val/1e9:.2f}B"
    elif val >= 1e6:
        return f"${val/1e6:.2f}M"
    elif val >= 1e3:
        return f"${val/1e3:.2f}k"
    return f"${val:.2f}"

SP500_CACHE_FILE = "data/sp500_cache.json"

def get_dynamic_sp500_list() -> List[Dict[str, str]]:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SP500_CACHE_FILE):
        if (time.time() - os.path.getmtime(SP500_CACHE_FILE)) < 86400:
            try:
                with open(SP500_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        tables = pd.read_html(resp.text)
        sp_table = tables[0]
        sp500_list = [{"symbol": str(r['Symbol']).replace('.', '-'), "name": str(r['Security'])} for _, r in sp_table.iterrows()]
        with open(SP500_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(sp500_list, f, indent=2, ensure_ascii=False)
        return sp500_list
    except Exception:
        return [
            {"symbol": "NVDA", "name": "Nvidia"}, {"symbol": "AAPL", "name": "Apple"},
            {"symbol": "MSFT", "name": "Microsoft"}, {"symbol": "AMZN", "name": "Amazon"},
            {"symbol": "GOOGL", "name": "Alphabet"}, {"symbol": "META", "name": "Meta"},
            {"symbol": "TSLA", "name": "Tesla"}, {"symbol": "BRK-B", "name": "Berkshire"},
            {"symbol": "AVGO", "name": "Broadcom"}, {"symbol": "JPM", "name": "JPMorgan"}
        ]

MARKET_CATALOG = {
    "forex": [
        {"symbol": "EURUSD=X", "name": "EUR / USD"}, {"symbol": "GBPUSD=X", "name": "GBP / USD"},
        {"symbol": "USDJPY=X", "name": "USD / JPY"}, {"symbol": "USDCHF=X", "name": "USD / CHF"},
        {"symbol": "AUDUSD=X", "name": "AUD / USD"}, {"symbol": "USDCAD=X", "name": "USD / CAD"}
    ],
    "commodities": [
        {"symbol": "GC=F", "name": "Or (Gold)"}, {"symbol": "SI=F", "name": "Argent (Silver)"},
        {"symbol": "CL=F", "name": "Pétrole Brut WTI"}, {"symbol": "BZ=F", "name": "Pétrole Brent"},
        {"symbol": "HG=F", "name": "Cuivre (Copper)"}, {"symbol": "NG=F", "name": "Gaz Naturel"}
    ],
    "indices": [
        {"symbol": "^GSPC", "name": "S&P 500 (US)"}, {"symbol": "^IXIC", "name": "Nasdaq Composite"},
        {"symbol": "^DJI", "name": "Dow Jones 30"}, {"symbol": "^FCHI", "name": "CAC 40 (France)"},
        {"symbol": "^GDAXI", "name": "DAX 40 (Allemagne)"}, {"symbol": "^N225", "name": "Nikkei 225 (Japon)"}
    ],
    "etf": [
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"}, {"symbol": "QQQ", "name": "Invesco QQQ"},
        {"symbol": "SMH", "name": "VanEck Semiconductor ETF"}, {"symbol": "GLD", "name": "SPDR Gold Shares"},
        {"symbol": "TLT", "name": "iShares 20+ Year Treasury"}, {"symbol": "IWM", "name": "iShares Russell 2000"}
    ]
}

class UnifiedMarketProvider:
    @staticmethod
    def get_market_assets(category: str, limit: int = 50) -> List[Dict[str, str]]:
        if category == "stocks":
            return get_dynamic_sp500_list()[:limit]
        return MARKET_CATALOG.get(category, [])[:limit]

    @staticmethod
    def fetch_and_analyze(symbol: str, timeframe: str = '1wk', period: str = '2y') -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=timeframe)
            if df.empty or len(df) < 25:
                return {}

            df['ma5'] = TechnicalIndicators.calculate_ema(df['Close'], span=5)
            df['ma20'] = TechnicalIndicators.calculate_ema(df['Close'], span=20)
            df['ma80'] = TechnicalIndicators.calculate_ema(df['Close'], span=80)
            df['rsi21'] = TechnicalIndicators.calculate_rsi(df['Close'], period=21)

            bbw_res = TechnicalIndicators.calculate_paolo_bbw_compression(df, period=80, dev=2.0, lookback=52)
            df['bbw'] = bbw_res['bbw_series']
            df['bbw_min'] = bbw_res['min_lookback_series']

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            rsi21_strat = TechnicalIndicators.evaluate_rsi21_polarity_strategy(df)

            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            change_pct = ((last_close - prev_close) / prev_close) * 100

            try:
                hist_max = ticker.history(period="max", interval="1mo")
                ath_price = float(hist_max['High'].max()) if not hist_max.empty else float(df['High'].max())
            except Exception:
                ath_price = float(df['High'].max())

            ath_price = max(ath_price, float(df['High'].max()))
            dist_ath_pct = ((last_close - ath_price) / ath_price) * 100 if ath_price > 0 else 0.0

            mcap = None
            try:
                mcap = ticker.fast_info.market_cap
            except Exception:
                pass

            vol_val = float(df['Volume'].iloc[-1]) * last_close if 'Volume' in df.columns else 0

            return {
                "symbol": symbol,
                "price": round(last_close, 4 if "USD" in symbol or "=X" in symbol else 2),
                "df_m5": float(df['ma5'].iloc[-1]),
                "df_m20": float(df['ma20'].iloc[-1]),
                "df_m80": float(df['ma80'].iloc[-1]),
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(vol_val),
                "market_cap": fmt_currency(mcap) if mcap else "N/A",
                "ath_price": round(ath_price, 2),
                "dist_ath_pct": round(dist_ath_pct, 2),
                "rsi": round(float(df['rsi21'].iloc[-1]), 1),
                "rsi_zone": TechnicalIndicators.evaluate_rsi_zone(float(df['rsi21'].iloc[-1])),
                "bbw": bbw_res['current_bbw'],
                "bbw_min": bbw_res['min_bbw'],
                "bbw_squeeze": bbw_res['is_squeeze'],
                "bbw_status": bbw_res['status'],
                "regime": regime,
                "state": state,
                "rsi21_strat": rsi21_strat,
                "rsi_polarity": rsi21_strat['polarity'],
                "rsi_state": rsi21_strat['state'],
                "rsi_sl": rsi21_strat['sl_price'],
                "rsi_tp1": rsi21_strat['tp1_price'],
                "df": df
            }
        except Exception:
            return {}
