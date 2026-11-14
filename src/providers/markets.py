import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

MARKET_CATALOG = {
    "stocks": [
        {"symbol": "NVDA", "name": "Nvidia"},
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "GOOGL", "name": "Alphabet (Google)"},
        {"symbol": "META", "name": "Meta Platforms"},
        {"symbol": "TSLA", "name": "Tesla"},
        {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
        {"symbol": "AVGO", "name": "Broadcom"},
        {"symbol": "JPM", "name": "JPMorgan Chase"}
    ],
    "forex": [
        {"symbol": "EURUSD=X", "name": "EUR / USD"},
        {"symbol": "GBPUSD=X", "name": "GBP / USD"},
        {"symbol": "USDJPY=X", "name": "USD / JPY"},
        {"symbol": "USDCHF=X", "name": "USD / CHF"},
        {"symbol": "AUDUSD=X", "name": "AUD / USD"},
        {"symbol": "USDCAD=X", "name": "USD / CAD"},
        {"symbol": "EURGBP=X", "name": "EUR / GBP"}
    ],
    "commodities": [
        {"symbol": "GC=F", "name": "Or (Gold)"},
        {"symbol": "SI=F", "name": "Argent (Silver)"},
        {"symbol": "CL=F", "name": "Pétrole Brut WTI"},
        {"symbol": "BZ=F", "name": "Pétrole Brent"},
        {"symbol": "HG=F", "name": "Cuivre (Copper)"},
        {"symbol": "NG=F", "name": "Gaz Naturel"}
    ],
    "indices": [
        {"symbol": "^GSPC", "name": "S&P 500 (US)"},
        {"symbol": "^IXIC", "name": "Nasdaq Composite"},
        {"symbol": "^DJI", "name": "Dow Jones 30"},
        {"symbol": "^FCHI", "name": "CAC 40 (France)"},
        {"symbol": "^GDAXI", "name": "DAX 40 (Allemagne)"},
        {"symbol": "^N225", "name": "Nikkei 225 (Japon)"}
    ],
    "etf": [
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ (Nasdaq 100)"},
        {"symbol": "SMH", "name": "VanEck Semiconductor ETF"},
        {"symbol": "GLD", "name": "SPDR Gold Shares"},
        {"symbol": "TLT", "name": "iShares 20+ Year Treasury"},
        {"symbol": "IWM", "name": "iShares Russell 2000"}
    ]
}

class UnifiedMarketProvider:
    @staticmethod
    def get_market_assets(category: str) -> List[Dict[str, str]]:
        return MARKET_CATALOG.get(category, [])

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
            last_price = float(df['Close'].iloc[-1])

            return {
                "symbol": symbol,
                "price": round(last_price, 4 if "USD" in symbol else 2),
                "regime": regime,
                "state": state,
                "df": df
            }
        except Exception:
            return {}
