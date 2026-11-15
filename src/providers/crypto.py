import ccxt
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

_CRYPTO_META_CACHE = {}

def get_crypto_metadata():
    global _CRYPTO_META_CACHE
    if not _CRYPTO_META_CACHE:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=150&page=1"
            resp = requests.get(url, timeout=6).json()
            for c in resp:
                sym = c['symbol'].upper()
                _CRYPTO_META_CACHE[sym] = {
                    "market_cap": c.get('market_cap', 0)
                }
        except Exception:
            pass
    return _CRYPTO_META_CACHE

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

    def analyze_ticker(self, symbol: str, timeframe: str = '1w', limit: int = 350) -> Dict[str, Any]:
        try:
            if "/" not in symbol and symbol.endswith("USDT"):
                symbol = f"{symbol[:-4]}/USDT"
                
            # Récupération d'un historique profond (jusqu'à 350 semaines) pour un ATH fiable
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
            df['rsi21'] = TechnicalIndicators.calculate_rsi(df['Close'], period=21)

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            
            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            change_pct = ((last_close - prev_close) / prev_close) * 100
            last_vol_usd = float(df['volume'].iloc[-1]) * last_close

            # VRAI ATH DE MARCHÉ (Calculé sur l'historique effectif de négociation)
            ath_price = float(df['High'].max())
            dist_ath_pct = ((last_close - ath_price) / ath_price) * 100 if ath_price > 0 else 0.0

            # Métadonnées Capitalisation
            base_coin = symbol.split('/')[0].upper()
            meta = get_crypto_metadata().get(base_coin, {})
            cap_val = meta.get("market_cap", 0)

            # Détection d'opportunité d'entrée (Pullback MM20)
            ma20 = float(df['ma20'].iloc[-1])
            dist_ma20 = abs(last_close - ma20) / ma20 if ma20 else 1.0
            is_entry_zone = False
            entry_type = ""
            
            if state == "state_new_buy":
                is_entry_zone = True
                entry_type = "🔥 Signal Achat Déclenché"
            elif regime == "regime_bull" and dist_ma20 <= 0.04 and last_close >= ma20:
                is_entry_zone = True
                entry_type = "🎯 Rebond Support MM20"

            return {
                "symbol": symbol,
                "price": round(last_close, 4),
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(last_vol_usd),
                "market_cap": fmt_currency(cap_val) if cap_val else "N/A",
                "ath_price": round(ath_price, 4),
                "rsi": round(float(df['rsi21'].iloc[-1]), 1),
                "rsi_zone": TechnicalIndicators.evaluate_rsi_zone(float(df['rsi21'].iloc[-1])),
                "dist_ath_pct": round(dist_ath_pct, 2),
                "regime": regime,
                "state": state,
                "is_entry_zone": is_entry_zone,
                "entry_type": entry_type,
                "df": df
            }
        except Exception:
            return {}
