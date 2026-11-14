import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

class USStocksProvider:
    # Sélection des méga-capitalisations et leaders du S&P 500
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

    def analyze_stock(self, symbol: str, timeframe: str = '1wk', period: str = '2y') -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=timeframe)
            
            if df.empty or len(df) < 25:
                return {}

            # Calcul des MM 5, 20 et 80
            df['ma5'] = TechnicalIndicators.calculate_ema(df['Close'], span=5)
            df['ma20'] = TechnicalIndicators.calculate_ema(df['Close'], span=20)
            df['ma80'] = TechnicalIndicators.calculate_ema(df['Close'], span=80)
            df['close'] = df['Close']

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
