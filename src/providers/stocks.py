import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")
try:
    import pandas as pd
    from pandas.errors import Pandas4Warning, PandasChangeWarning
    warnings.filterwarnings("ignore", category=Pandas4Warning)
    warnings.filterwarnings("ignore", category=PandasChangeWarning)
except Exception:
    pass

import yfinance as yf
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

class USStocksProvider:
    DEFAULT_SP500 = [
        {"symbol": "NVDA", "name": "Nvidia"},
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "GOOGL", "name": "Alphabet (Google)"},
        {"symbol": "META", "name": "Meta Platforms"},
        {"symbol": "TSLA", "name": "Tesla"},
        {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
        {"symbol": "AVGO", "name": "Broadcom"},
        {"symbol": "JPM", "name": "JPMorgan Chase"},
        {"symbol": "LLY", "name": "Eli Lilly"},
        {"symbol": "V", "name": "Visa"},
        {"symbol": "WMT", "name": "Walmart"},
        {"symbol": "XOM", "name": "ExxonMobil"},
        {"symbol": "MA", "name": "Mastercard"}
    ]

    def get_sp500_tickers(self, limit: int = 15) -> List[Dict[str, str]]:
        return self.DEFAULT_SP500[:limit]

    def analyze_stock(self, symbol: str, timeframe: str = '1wk', period: str = '10y') -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=timeframe)
            
            if df.empty or len(df) < 25:
                return {}

            # Normalisation des colonnes
            df['Close'] = df['Close'] if 'Close' in df.columns else df['close']
            df['Open'] = df['Open'] if 'Open' in df.columns else df['open']
            df['High'] = df['High'] if 'High' in df.columns else df['high']
            df['Low'] = df['Low'] if 'Low' in df.columns else df['low']
            df['close'] = df['Close']

            # Moyennes Mobiles Simples (SMA) et RSI 21 (identique à markets.py)
            df['ma5'] = TechnicalIndicators.calculate_sma(df['Close'], window=5)
            df['ma20'] = TechnicalIndicators.calculate_sma(df['Close'], window=20)
            df['ma80'] = TechnicalIndicators.calculate_sma(df['Close'], window=80)
            df['ma320'] = TechnicalIndicators.calculate_sma(df['Close'], window=320)
            df['rsi21'] = TechnicalIndicators.calculate_rsi(df['Close'], period=21)

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            last_price = float(df['Close'].iloc[-1])

            return {
                "symbol": symbol,
                "price": round(last_price, 2),
                "regime": regime,
                "state": state
            }
        except Exception:
            return {}
