import ccxt
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

class BinanceCryptoProvider:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_top_pairs(self, quote: str = "USDT", limit: int = 50) -> List[Dict[str, Any]]:
        try:
            self.exchange.load_markets()
            tickers = self.exchange.fetch_tickers()
            usdt_pairs = [
                t for sym, t in tickers.items() 
                if sym.endswith(f"/{quote}") and t.get('quoteVolume') is not None
            ]
            usdt_pairs.sort(key=lambda x: x.get('quoteVolume', 0), reverse=True)
            return usdt_pairs[:limit]
        except Exception:
            return []

    def analyze_ticker(self, symbol: str, timeframe: str = '1w', limit: int = 150) -> Dict[str, Any]:
        try:
            if "/" not in symbol and symbol.endswith("USDT"):
                symbol = f"{symbol[:-4]}/USDT"
                
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

            df['ma5'] = TechnicalIndicators.calculate_ema(df['Close'], span=5)
            df['ma20'] = TechnicalIndicators.calculate_ema(df['Close'], span=20)
            df['ma80'] = TechnicalIndicators.calculate_ema(df['Close'], span=80)

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            
            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            change_pct = ((last_close - prev_close) / prev_close) * 100

            # Volume en valeur sur la bougie
            last_vol_usd = float(df['volume'].iloc[-1]) * last_close

            return {
                "symbol": symbol,
                "price": round(last_close, 4),
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(last_vol_usd),
                "market_cap": "N/A (Crypto Spot)",
                "regime": regime,
                "state": state,
                "df": df
            }
        except Exception:
            return {}
