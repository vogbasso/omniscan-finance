import json
import os

print("[1/5] Mise à jour des traductions...")
with open("config/locales/fr.json", "r", encoding="utf-8") as f:
    fr = json.load(f)
fr["col_rsi"] = "RSI (21)"
fr["rsi_overbought"] = "🔴 Surachat (≥70)"
fr["rsi_oversold"] = "🟢 Survente (≤30)"
fr["rsi_neutral"] = "⚪ Neutre (45-55)"
fr["rsi_bullish"] = "↗️ Haussier (55-70)"
fr["rsi_bearish"] = "↘️ Baissier (30-45)"
with open("config/locales/fr.json", "w", encoding="utf-8") as f:
    json.dump(fr, f, indent=2, ensure_ascii=False)

print("[2/5] Déploiement de src/core/indicators.py...")
indicators_code = '''import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

class TechnicalIndicators:
    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 21) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def evaluate_rsi_zone(rsi_val: float) -> str:
        if rsi_val >= 70:
            return "rsi_overbought"
        elif rsi_val <= 30:
            return "rsi_oversold"
        elif 45 <= rsi_val <= 55:
            return "rsi_neutral"
        elif rsi_val > 55:
            return "rsi_bullish"
        else:
            return "rsi_bearish"

    @staticmethod
    def calculate_paolo_bbw_compression(df: pd.DataFrame, period: int = 80, dev: float = 2.0, lookback: int = 52) -> Dict[str, Any]:
        close = df['Close']
        middle = df['ma80'] if 'ma80' in df.columns else close.ewm(span=period, adjust=False).mean()
        rolling_std = close.rolling(window=period, min_periods=25).std().fillna(close.std())

        upper = middle + (dev * rolling_std)
        lower = middle - (dev * rolling_std)
        bbw_series = ((upper - lower) / middle.replace(0, 1e-9)) * 100.0
        bbw_series = bbw_series.fillna(0.0)
        min_lookback_series = bbw_series.rolling(window=lookback, min_periods=15).min().fillna(bbw_series)

        last_bbw = float(bbw_series.iloc[-1])
        last_min = float(min_lookback_series.iloc[-1])
        is_squeeze = (last_bbw <= last_min * 1.08) or (last_bbw <= last_min)
        
        prev_bbw = float(bbw_series.iloc[-2]) if len(bbw_series) > 1 else last_bbw
        is_expansion = (last_bbw > prev_bbw * 1.15) and not is_squeeze
        status = "bbw_squeeze" if is_squeeze else ("bbw_expansion" if is_expansion else "bbw_normal")

        return {
            "bbw_series": bbw_series,
            "min_lookback_series": min_lookback_series,
            "current_bbw": round(last_bbw, 2),
            "min_bbw": round(last_min, 2),
            "is_squeeze": is_squeeze,
            "status": status
        }

    @staticmethod
    def evaluate_regime_and_state(df: pd.DataFrame) -> Tuple[str, str]:
        regime = "regime_bull" if df['ma20'].iloc[0] > df['ma80'].iloc[0] else "regime_bear"
        is_fresh_signal = False
        last_signal = None

        for i in range(len(df)):
            p = float(df['close'].iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            m80 = float(df['ma80'].iloc[i])

            if m20 > m80 and (p < m5 and p < m20 and p < m80):
                if regime != "regime_bear":
                    regime = "regime_bear"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_sell"

            elif m20 < m80 and (p > m5 and p > m20 and p > m80):
                if regime != "regime_bull":
                    regime = "regime_bull"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_buy"

        if is_fresh_signal and last_signal:
            return regime, last_signal

        last_p = float(df['close'].iloc[-1])
        last_m5 = float(df['ma5'].iloc[-1])
        last_m20 = float(df['ma20'].iloc[-1])
        last_m80 = float(df['ma80'].iloc[-1])

        if last_m5 > last_m20 > last_m80:
            state = "state_strong_bull"
        elif last_m5 < last_m20 < last_m80:
            state = "state_strong_bear"
        elif last_m20 > last_m80 and (last_m80 < last_m5 < last_m20):
            state = "state_slowdown_bull"
        elif last_m20 < last_m80 and (last_m20 < last_m5 < last_m80):
            state = "state_slowdown_bear"
        else:
            state = "state_consolidation"

        return regime, state

    @staticmethod
    def evaluate_rsi21_polarity_strategy(df: pd.DataFrame) -> Dict[str, Any]:
        polarity = False
        has_touched_oversold = False
        oversold_lowest_low = None
        current_pullback_lowest = None
        pullback_confirmed = False
        trade_count = 0
        last_signal_event = None
        active_trade = None

        n = len(df)
        for i in range(n):
            rsi = float(df['rsi21'].iloc[i])
            low = float(df['Low'].iloc[i])
            close = float(df['Close'].iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            prev_m5 = float(df['ma5'].iloc[i-1]) if i > 0 else m5
            prev_m20 = float(df['ma20'].iloc[i-1]) if i > 0 else m20

            if rsi <= 30:
                has_touched_oversold = True
                oversold_lowest_low = low if oversold_lowest_low is None else min(oversold_lowest_low, low)

            if has_touched_oversold and rsi >= 70:
                polarity = True
                has_touched_oversold = False
                pullback_confirmed = False

            if polarity:
                if rsi < 50:
                    if not pullback_confirmed:
                        pullback_confirmed = True
                        current_pullback_lowest = low
                    else:
                        current_pullback_lowest = min(current_pullback_lowest, low)

                is_crossover = (prev_m5 <= prev_m20 and m5 > m20)
                if pullback_confirmed and is_crossover:
                    trade_count += 1
                    if trade_count == 1:
                        sl = oversold_lowest_low if oversold_lowest_low is not None else low
                        t_type = "Trade 1 (Post-Survente)"
                    else:
                        sl = current_pullback_lowest if current_pullback_lowest is not None else low
                        t_type = f"Trade {trade_count} (Post-Pullback < 50)"

                    risk = close - sl
                    tp1 = close + risk if risk > 0 else close * 1.05
                    pullback_confirmed = False
                    current_pullback_lowest = None

                    active_trade = {
                        "entry": close,
                        "sl": sl,
                        "tp1": tp1,
                        "trade_type": t_type
                    }
                    if i == n - 1:
                        last_signal_event = "signal_buy_fresh"

        last_rsi = float(df['rsi21'].iloc[-1])
        if last_signal_event == "signal_buy_fresh" and active_trade:
            state = "STATE_FRESH_BUY"
        elif polarity and pullback_confirmed:
            state = "STATE_PULLBACK_50"
        elif polarity and last_rsi >= 70:
            state = "STATE_OVERBOUGHT_IMPULSE"
        elif polarity:
            state = "STATE_BULLISH_TREND"
        else:
            state = "STATE_WAIT_POLARITY"

        return {
            "polarity": "POLARITY_BULL" if polarity else "POLARITY_WAIT",
            "state": state,
            "trade_count": trade_count,
            "sl_price": round(active_trade['sl'], 4) if active_trade else None,
            "tp1_price": round(active_trade['tp1'], 4) if active_trade else None,
            "trade_type": active_trade['trade_type'] if active_trade else ""
        }
'''
with open("src/core/indicators.py", "w", encoding="utf-8") as f:
    f.write(indicators_code)

print("[3/5] Déploiement de src/providers/crypto.py...")
crypto_code = '''import ccxt
import requests
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

STABLECOINS = {
    "USDT", "USDC", "FDUSD", "USDE", "USD1", "DAI", "TUSD", "USDD", 
    "PYUSD", "BUSD", "GUSD", "USDP", "FRAX", "LUSD", "USD0", "SUSD",
    "USTC", "USDJ", "CUSD", "EURS", "EURC", "AEUR", "EURI", "WBTC", "BTCB"
}

_COINGECKO_CACHE = []

def get_top_cryptos_by_market_cap():
    global _COINGECKO_CACHE
    if not _COINGECKO_CACHE:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=150&page=1"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=8).json()
            if isinstance(resp, list):
                _COINGECKO_CACHE = resp
        except Exception:
            pass
    return _COINGECKO_CACHE

class BinanceCryptoProvider:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_top_pairs(self, quote: str = "USDT", limit: int = 50) -> List[Dict[str, Any]]:
        try:
            self.exchange.load_markets()
            available = set(self.exchange.symbols)
            cg = get_top_cryptos_by_market_cap()
            selected = []
            if cg:
                for c in cg:
                    base = c['symbol'].upper()
                    if base in STABLECOINS or base.startswith("USD"):
                        continue
                    pair = f"{base}/{quote}"
                    if pair in available:
                        selected.append({
                            "symbol": pair,
                            "name": c.get("name", base),
                            "market_cap": c.get("market_cap", 0),
                            "ath": c.get("ath", 0)
                        })
                    if len(selected) >= limit:
                        break

            if not selected:
                tickers = self.exchange.fetch_tickers()
                for sym in tickers.keys():
                    if sym.endswith(f"/{quote}"):
                        base = sym.split('/')[0].upper()
                        if base not in STABLECOINS and not base.startswith("USD"):
                            selected.append({"symbol": sym, "name": base, "market_cap": 0, "ath": 0})
                    if len(selected) >= limit:
                        break
            return selected
        except Exception:
            return []

    def analyze_ticker(self, symbol: str, timeframe: str = '1w', limit: int = 350, meta_info: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if "/" not in symbol and symbol.endswith("USDT"):
                symbol = f"{symbol[:-4]}/USDT"

            base_coin = symbol.split('/')[0].upper()
            if base_coin in STABLECOINS or base_coin.startswith("USD"):
                return {}

            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if len(ohlcv) < 25:
                return {}

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('Date', inplace=True)
            df['Close'] = df['close']
            df['Open'] = df['open']
            df['High'] = df['high']
            df['Low'] = df['low']

            last_close = float(df['Close'].iloc[-1])
            if 0.985 <= last_close <= 1.015 and df['Close'].std() < 0.02:
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

            prev_close = float(df['Close'].iloc[-2])
            change_pct = ((last_close - prev_close) / prev_close) * 100
            last_vol_usd = float(df['volume'].iloc[-1]) * last_close

            ath_price = float(df['High'].max())
            dist_ath_pct = ((last_close - ath_price) / ath_price) * 100 if ath_price > 0 else 0.0
            cap_val = meta_info.get("market_cap", 0) if meta_info else 0

            return {
                "symbol": symbol,
                "price": round(last_close, 4),
                "df_m5": float(df['ma5'].iloc[-1]),
                "df_m20": float(df['ma20'].iloc[-1]),
                "df_m80": float(df['ma80'].iloc[-1]),
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(last_vol_usd),
                "market_cap": fmt_currency(cap_val) if cap_val else "N/A",
                "ath_price": round(ath_price, 4),
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
'''
with open("src/providers/crypto.py", "w", encoding="utf-8") as f:
    f.write(crypto_code)

print("[4/5] Déploiement de src/providers/markets.py...")
markets_code = '''import os
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
'''
with open("src/providers/markets.py", "w", encoding="utf-8") as f:
    f.write(markets_code)

print("[5/5] Déploiement de app.py avec le Sélecteur de Stratégie...")
app_code = '''import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

from src.providers.crypto import BinanceCryptoProvider
from src.providers.markets import UnifiedMarketProvider

st.set_page_config(
    page_title="OmniScan Finance - Screener RSI 21 & MM 5/20/80",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

st.sidebar.title("🌐 OmniScan Finance")
st.sidebar.caption("Architecte & Auteur : **Vogel Paolo BASSO**")

lang = st.sidebar.selectbox("Langue / Language", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"
t = load_locale(lang_code)

st.sidebar.markdown("---")
strategy_choice = st.sidebar.radio(
    "Méthode d'Analyse" if lang_code == "fr" else "Strategy",
    options=[
        "🌟 RSI 21 / MM 5-20 / Pullback 50 (Défaut)",
        "📊 Triple MM 5 / 20 / 80 (Regime & BBW)"
    ],
    index=0
)
is_rsi_strategy = "RSI 21" in strategy_choice

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ " + ("Configuration du Scan" if lang_code == "fr" else "Scan Settings"))

market_options = {
    "crypto": t["menu_crypto"],
    "stocks": t["menu_stocks"],
    "forex": t["menu_forex"],
    "commodities": t["menu_commodities"],
    "indices": t["menu_indices"],
    "etf": t["menu_etf"]
}

selected_category = st.sidebar.selectbox(
    "Choisir la catégorie" if lang_code == "fr" else "Select category",
    options=list(market_options.keys()),
    format_func=lambda x: market_options[x]
)

scan_limit = st.sidebar.slider(
    "Nombre d'actifs" if lang_code == "fr" else "Number of assets",
    min_value=10, max_value=100, value=25, step=5
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 " + ("Recherche Ciblée" if lang_code == "fr" else "Targeted Search"))
custom_search = st.sidebar.text_input("Ticker personnalisé (ex: BTC/USDT, NVDA)", value="").strip().upper()

timeframe_display = "Hebdomadaire (Weekly - 1w)" if lang_code == "fr" else "Weekly (1w)"
st.sidebar.info(f"⏱️ **Timeframe** : {timeframe_display}")

if is_rsi_strategy:
    st.title("🌟 OmniScan Finance — Stratégie RSI 21 / Pullback 50 & MM 5-20")
    st.caption("Polarité haussière (Survente $\le 30 \rightarrow$ Surachat $\ge 70$) • Pullback sous 50 • Crossover MM 5/20 • Long Only")
else:
    st.title("📊 OmniScan Finance — Stratégie Triple MM 5 / 20 / 80")
    st.caption("Régime de fond avec mémoire d'état • Faisceau 5/20/80 • Compression Paolo BBW")

@st.cache_data(ttl=300, show_spinner=False)
def get_scanned_data(category: str, limit: int):
    results = []
    charts = {}
    if category == "crypto":
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=limit)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe="1w", limit=250, meta_info=p)
            if data:
                data["name"] = p.get("name", p['symbol'].split('/')[0])
                charts[data["symbol"]] = data.pop("df", None)
                results.append(data)
    else:
        assets = UnifiedMarketProvider.get_market_assets(category, limit=limit)
        for item in assets:
            data = UnifiedMarketProvider.fetch_and_analyze(item["symbol"], timeframe="1wk")
            if data:
                data["name"] = item["name"]
                charts[item["symbol"]] = data.pop("df", None)
                results.append(data)
    return results, charts

with st.spinner("Analyse quantitative des flux..." if lang_code == "fr" else "Running scan..."):
    results, charts_cache = get_scanned_data(selected_category, scan_limit)

if results:
    st.markdown("---")
    if is_rsi_strategy:
        fresh_rsi_buys = [r for r in results if r.get("rsi_state") == "STATE_FRESH_BUY"]
        pullback_setups = [r for r in results if r.get("rsi_state") == "STATE_PULLBACK_50"]

        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT FRAIS (CROISEMENT MM5 > MM20 APRÈS PULLBACK < 50)")
        if fresh_rsi_buys:
            st.success(f"🔥 ALERTE ACHAT MAJEURE : {len(fresh_rsi_buys)} signal(ux) d'achat validé(s) !")
            cols1 = st.columns(min(len(fresh_rsi_buys), 4))
            for idx, sig in enumerate(fresh_rsi_buys[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
                    st.write(f"**Type** : `{sig.get('rsi21_strat', {}).get('trade_type', 'Achat Long')}`")
                    st.write(f"**Stop Loss** : `${sig.get('rsi_sl')}`")
                    st.write(f"**Objectif TP1 (1:1)** : `${sig.get('rsi_tp1')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais déclenché cette semaine sur la stratégie RSI 21.")

        st.markdown("---")
        st.subheader("🔭 RADAR 2 : ZONE DE VEILLE (PULLBACK SOUS 50 EN COURS — ATTENTE DU CROISEMENT MM5/20)")
        if pullback_setups:
            st.warning(f"👀 {len(pullback_setups)} actif(s) en respiration saine sous 50 (À l'affût du croisement MM 5 > 20) !")
            cols2 = st.columns(min(len(pullback_setups), 4))
            for idx, pb in enumerate(pullback_setups[:4]):
                with cols2[idx]:
                    st.markdown(f"#### **{pb['name']}** ({pb['symbol']})")
                    st.write(f"**Prix Actuel** : `${pb['price']}`")
                    st.write(f"**RSI (21)** : `{pb.get('rsi')} (< 50 Confirmé)`")
                    st.write(f"**MM5** : `${round(pb.get('df_m5', pb.get('price')), 2)}` | **MM20** : `${round(pb.get('df_m20', pb.get('price')), 2)}`")
                    st.write(f"**Paolo BBW** : `{pb.get('bbw')}%`")
        else:
            st.info("ℹ️ Aucun actif actuellement en phase de pullback sous 50.")
    else:
        fresh_signals = [r for r in results if r.get("state") == "state_new_buy"]
        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT FRAIS (5/20/80)")
        if fresh_signals:
            st.success(f"🔥 {len(fresh_signals)} signal(ux) frais détecté(s) !")
            cols1 = st.columns(min(len(fresh_signals), 4))
            for idx, sig in enumerate(fresh_signals[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
                    st.write(f"**RSI (21)** : `{sig.get('rsi')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais 5/20/80 cette semaine.")

    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Actifs Scannés", len(results))
    bull_count = sum(1 for r in results if (r.get("rsi_polarity") == "POLARITY_BULL" if is_rsi_strategy else r.get("regime") == "regime_bull"))
    k2.metric("🟢 Polarité Acheteuse" if is_rsi_strategy else "🟢 Régime Acheteur", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
    k3.metric("RSI Moyen", round(sum(r.get("rsi", 50) for r in results) / len(results), 1))
    squeeze_count = sum(1 for r in results if r.get("bbw_squeeze"))
    k4.metric("⚡ Squeeze Paolo BBW", squeeze_count)

    st.markdown("---")
    st.subheader("📋 " + ("Résultats Détaillés du Marché" if lang_code == "fr" else "Detailed Market Results"))
    search_f = st.text_input("🔎 Filtrer dans la liste :", "").strip().upper()

    table_data = []
    for r in results:
        if search_f and search_f not in r["symbol"] and search_f not in r.get("name", "").upper():
            continue
        chg_val = r["change_pct"]
        chg_str = f"▲ +{chg_val:.2f}%" if chg_val > 0 else (f"▼ {chg_val:.2f}%" if chg_val < 0 else "  0.00%")
        rsi_val = r.get("rsi", 50.0)
        rsi_display = f"{rsi_val} | {t.get(r.get('rsi_zone', 'rsi_neutral'), '')}"
        bbw_val = r.get("bbw", 0.0)
        bbw_str = f"⚡ {bbw_val:.1f}% (Squeeze)" if r.get("bbw_squeeze") else f"{bbw_val:.1f}%"

        if is_rsi_strategy:
            polarity_label = "🟢 ACHETEUSE" if r.get("rsi_polarity") == "POLARITY_BULL" else "⚪ ATTENTE"
            r_state = r.get("rsi_state", "")
            if r_state == "STATE_FRESH_BUY":
                statut_str = "🔥 SIGNAL ACHAT ACTIF"
            elif r_state == "STATE_PULLBACK_50":
                statut_str = "⏳ PULLBACK < 50"
            elif r_state == "STATE_OVERBOUGHT_IMPULSE":
                statut_str = "🚀 IMPULSION (RSI ≥ 70)"
            elif r_state == "STATE_BULLISH_TREND":
                statut_str = "↗️ FLUX ACHETEUR"
            else:
                statut_str = "⚪ ATTENTE CYCLE"

            sl_str = f"${r.get('rsi_sl')}" if r.get('rsi_sl') else "—"
            tp1_str = f"${r.get('rsi_tp1')}" if r.get('rsi_tp1') else "—"

            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "MM5": f"${r.get('df_m5', r['price']):.2f}",
                "MM20": f"${r.get('df_m20', r['price']):.2f}",
                "MM80": f"${r.get('df_m80', r['price']):.2f}",
                "RSI (21)": rsi_display,
                "Polarité": polarity_label,
                "État Stratégie": statut_str,
                "Stop Loss": sl_str,
                "TP1 (1:1)": tp1_str,
                "Paolo BBW (80)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        else:
            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "MM5": f"${r.get('df_m5', r['price']):.2f}",
                "MM20": f"${r.get('df_m20', r['price']):.2f}",
                "MM80": f"${r.get('df_m80', r['price']):.2f}",
                "RSI (21)": rsi_display,
                t["col_regime"]: t.get(r["regime"], r["regime"]),
                "État Stratégie": t.get(r["state"], r["state"]),
                "Paolo BBW (80)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        table_data.append(row)

    df_display = pd.DataFrame(table_data)

    def style_change(val):
        if "▲" in str(val):
            return "background-color: rgba(0, 230, 118, 0.18); color: #00e676; font-weight: bold;"
        elif "▼" in str(val):
            return "background-color: rgba(255, 82, 82, 0.18); color: #ff5252; font-weight: bold;"
        return ""

    def style_polarity(val):
        if "ACHETEUSE" in str(val) or "ACHETEUR" in str(val):
            return "background-color: rgba(0, 230, 118, 0.15); color: #00e676; font-weight: bold;"
        return "color: #9e9e9e;"

    def style_bbw(val):
        if "⚡" in str(val):
            return "background-color: rgba(30, 144, 255, 0.25); color: #1e90ff; font-weight: bold;"
        return ""

    styler = df_display.style
    try:
        col_pol = "Polarité" if is_rsi_strategy else t["col_regime"]
        styled_df = styler.map(style_change, subset=[t["col_change"]])\\
                          .map(style_polarity, subset=[col_pol])\\
                          .map(style_bbw, subset=["Paolo BBW (80)"])
        st.dataframe(styled_df, use_container_width=True, height=450)
    except Exception:
        st.dataframe(df_display, use_container_width=True, height=450)

    st.markdown("---")
    st.subheader("📈 Inspecteur Technique : Chandeliers + RSI 21 (Niveau 50) + Paolo BBW")
    selected_sym = st.selectbox("Sélectionnez un actif :", [r["symbol"] for r in results])
    df_chart = charts_cache.get(selected_sym)

    if df_chart is not None and not df_chart.empty:
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.55, 0.23, 0.22],
            subplot_titles=(
                f"Chandeliers & MM (5 / 20 / 80) — {selected_sym}",
                "RSI (21) • Survente ≤ 30 | Zone Centrale 50 | Surachat ≥ 70",
                "Paolo BBW % (Bandes 80) & Seuil Compression (Min Lookback)"
            )
        )
        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="Prix"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma5'], line=dict(color='#00d4ff', width=1.5), name='MM5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma20'], line=dict(color='#ffaa00', width=2), name='MM20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma80'], line=dict(color='#d000ff', width=2.5), name='MM80'), row=1, col=1)

        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['rsi21'], line=dict(color='#ffd600', width=2), name='RSI 21'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff5252", annotation_text="Surachat 70", row=2, col=1)
        fig.add_hline(y=50, line_dash="solid", line_color="#ffffff", annotation_text="Pivot 50 (Pullback)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00e676", annotation_text="Survente 30", row=2, col=1)

        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['bbw'], line=dict(color='#1e90ff', width=2), name='Paolo BBW %'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['bbw_min'], line=dict(color='#ff1744', width=1.5, dash='dot'), name='Seuil Compression (Min)'), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=820, xaxis_rangeslider_visible=False, margin=dict(l=40, r=40, t=50, b=30))
        fig.update_yaxes(title_text="Prix ($)", row=1, col=1)
        fig.update_yaxes(title_text="RSI", range=[10, 90], row=2, col=1)
        fig.update_yaxes(title_text="BBW %", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)
'''
with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

print("\n[✓] Tous les fichiers ont été générés et écrits avec succès !")
