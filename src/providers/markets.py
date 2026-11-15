import warnings
warnings.filterwarnings("ignore")

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

from src.providers.crypto import BinanceCryptoProvider

# Catalogue étendu
from src.providers.markets import MARKET_CATALOG

class UnifiedMarketProvider:
    @staticmethod
    def get_market_assets(category: str, limit: int = 50) -> List[Dict[str, str]]:
        assets = MARKET_CATALOG.get(category, [])
        return assets[:limit]

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
            df['close'] = df['Close']

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            change_pct = ((last_close - prev_close) / prev_close) * 100

            # Récupération du Market Cap ultra-rapide via fast_info
            mcap = None
            try:
                mcap = ticker.fast_info.market_cap
            except Exception:
                mcap = None

            # Volume en valeur sur la semaine
            vol_val = float(df['Volume'].iloc[-1]) * last_close if 'Volume' in df.columns else 0

            return {
                "symbol": symbol,
                "price": round(last_close, 4 if "USD" in symbol or "=X" in symbol else 2),
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(vol_val),
                "market_cap": fmt_currency(mcap) if mcap else "N/A",
                "regime": regime,
                "state": state,
                "df": df
            }
        except Exception:
            return {}
