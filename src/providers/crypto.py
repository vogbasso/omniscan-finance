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

    def analyze_ticker(self, symbol: str, timeframe: str = '1w', limit: int = 500, meta_info: Dict[str, Any] = None) -> Dict[str, Any]:
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

            # Calcul des MM
            df['ma5'] = TechnicalIndicators.calculate_sma(df['Close'], window=5)
            df['ma20'] = TechnicalIndicators.calculate_sma(df['Close'], window=20)
            df['ma80'] = TechnicalIndicators.calculate_sma(df['Close'], window=80)
            df['ma320'] = TechnicalIndicators.calculate_sma(df['Close'], window=320)
            df['rsi21'] = TechnicalIndicators.calculate_rsi(df['Close'], period=21)

            # Calcul explicite des deux BBW (80 et 320)
            bbw80_res = TechnicalIndicators.calculate_paolo_bbw_compression(df, period=80, dev=2.0, lookback=52)
            bbw320_res = TechnicalIndicators.calculate_paolo_bbw_compression(df, period=320, dev=2.0, lookback=52)
            df['bbw80'] = bbw80_res['bbw_series']
            df['bbw80_min'] = bbw80_res['min_lookback_series']
            df['bbw320'] = bbw320_res['bbw_series']
            df['bbw320_min'] = bbw320_res['min_lookback_series']

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            rsi21_strat = TechnicalIndicators.evaluate_rsi21_polarity_strategy(df)
            rsi_sma20_320_strat = TechnicalIndicators.evaluate_rsi21_sma20_320_strategy(df)

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
                "df_m320": float(df['ma320'].iloc[-1]),
                "bbw80": bbw80_res['current_bbw'],
                "bbw80_min": bbw80_res['min_bbw'],
                "bbw80_squeeze": bbw80_res['is_squeeze'],
                "bbw320": bbw320_res['current_bbw'],
                "bbw320_min": bbw320_res['min_bbw'],
                "bbw320_squeeze": bbw320_res['is_squeeze'],
                "change_pct": round(change_pct, 2),
                "volume": fmt_currency(last_vol_usd),
                "market_cap": fmt_currency(cap_val) if cap_val else "N/A",
                "ath_price": round(ath_price, 4),
                "dist_ath_pct": round(dist_ath_pct, 2),
                "rsi": round(float(df['rsi21'].iloc[-1]), 1),
                "rsi_zone": TechnicalIndicators.evaluate_rsi_zone(float(df['rsi21'].iloc[-1])),
                "regime": regime,
                "state": state,
                "rsi_sma20_320_strat": rsi_sma20_320_strat,
                "is_recent_entry": rsi_sma20_320_strat['is_recent_entry'],
                "freshness_badge": rsi_sma20_320_strat['freshness_badge'],
                "perf_since_entry": rsi_sma20_320_strat['perf_since_entry'],
                "is_imminent_setup": rsi_sma20_320_strat['is_imminent_setup'],
                "imminent_label": rsi_sma20_320_strat['imminent_label'],
                "macro_trend": rsi_sma20_320_strat['macro_trend'],
                "impulse_state": rsi_sma20_320_strat['state'],
                "impulse_sl": rsi_sma20_320_strat['sl_price'],
                "impulse_tp1": rsi_sma20_320_strat['tp1_price'],
                "impulse_tp2": rsi_sma20_320_strat['tp2_price'],
                "rsi21_strat": rsi21_strat,
                "rsi_polarity": rsi21_strat['polarity'],
                "rsi_state": rsi21_strat['state'],
                "rsi_sl": rsi21_strat['sl_price'],
                "rsi_tp1": rsi21_strat['tp1_price'],
                "trade_signals_history": rsi21_strat.get('trade_signals_history', []),
                "df": df
            }
        except Exception as e:
            return {}
