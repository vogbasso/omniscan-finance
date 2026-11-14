import ccxt
import pandas as pd
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

class BinanceCryptoProvider:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_top_pairs(self, quote: str = "USDT", limit: int = 15) -> List[Dict[str, Any]]:
        self.exchange.load_markets()
        tickers = self.exchange.fetch_tickers()
        usdt_pairs = [
            t for sym, t in tickers.items() 
            if sym.endswith(f"/{quote}") and t.get('quoteVolume') is not None
        ]
        usdt_pairs.sort(key=lambda x: x.get('quoteVolume', 0), reverse=True)
        return usdt_pairs[:limit]

    def analyze_ticker(self, symbol: str, timeframe: str = '1w', limit: int = 150) -> Dict[str, Any]:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if len(ohlcv) < 25:
                return {}

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['ma5'] = TechnicalIndicators.calculate_ema(df['close'], span=5)
            df['ma20'] = TechnicalIndicators.calculate_ema(df['close'], span=20)
            df['ma80'] = TechnicalIndicators.calculate_ema(df['close'], span=80)

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            last_price = float(df['close'].iloc[-1])

            return {
                "symbol": symbol,
                "price": round(last_price, 4),
                "regime": regime,
                "state": state
            }
        except Exception:
            return {}
