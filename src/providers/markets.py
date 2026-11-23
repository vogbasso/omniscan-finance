import os
import json
import time
import math
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from src.core.indicators import TechnicalIndicators

def fmt_currency(val: float) -> str:
    if val is None or math.isnan(val) or val == 0:
        return "N/A"
    abs_v = abs(val)
    if abs_v >= 1e12:
        return f"${val/1e12:.2f}T"
    elif abs_v >= 1e9:
        return f"${val/1e9:.2f}B"
    elif abs_v >= 1e6:
        return f"${val/1e6:.2f}M"
    elif abs_v >= 1e3:
        return f"${val/1e3:.2f}k"
    return f"${val:.2f}"

MARKET_CATALOG = {
    "retirement": [
        {"symbol": "BITW", "name": "Indice Crypto Top 10 (Bitwise Index)"},
        {"symbol": "URTH", "name": "Indice MSCI World (Actions Monde)"},
        {"symbol": "SPY", "name": "Indice S&P 500 (Grandes Valeurs US)"},
        {"symbol": "IJH", "name": "Indice S&P 400 (Moyennes Valeurs US MidCap)"},
        {"symbol": "GLD", "name": "Or Physique (Seul Actif Tangible - Gold)"}
    ],
    "stocks": [
        {"symbol": "NVDA", "name": "Nvidia"}, {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"}, {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "GOOGL", "name": "Alphabet (Google)"}, {"symbol": "META", "name": "Meta Platforms"},
        {"symbol": "TSLA", "name": "Tesla"}, {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
        {"symbol": "AVGO", "name": "Broadcom"}, {"symbol": "JPM", "name": "JPMorgan Chase"},
        {"symbol": "LLY", "name": "Eli Lilly"}, {"symbol": "V", "name": "Visa"},
        {"symbol": "WMT", "name": "Walmart"}, {"symbol": "XOM", "name": "ExxonMobil"},
        {"symbol": "MA", "name": "Mastercard"}, {"symbol": "ORCL", "name": "Oracle"},
        {"symbol": "COST", "name": "Costco"}, {"symbol": "HD", "name": "Home Depot"},
        {"symbol": "PG", "name": "Procter & Gamble"}, {"symbol": "NFLX", "name": "Netflix"},
        {"symbol": "BAC", "name": "Bank of America"}, {"symbol": "CRM", "name": "Salesforce"},
        {"symbol": "AMD", "name": "AMD"}, {"symbol": "PLTR", "name": "Palantir"},
        {"symbol": "DIS", "name": "Walt Disney"}, {"symbol": "COIN", "name": "Coinbase"}
    ],
    "forex": [
        {"symbol": "EURUSD=X", "name": "EUR / USD"}, {"symbol": "GBPUSD=X", "name": "GBP / USD"},
        {"symbol": "USDJPY=X", "name": "USD / JPY"}, {"symbol": "USDCHF=X", "name": "USD / CHF"},
        {"symbol": "AUDUSD=X", "name": "AUD / USD"}, {"symbol": "USDCAD=X", "name": "USD / CAD"},
        {"symbol": "NZDUSD=X", "name": "NZD / USD"}, {"symbol": "EURGBP=X", "name": "EUR / GBP"},
        {"symbol": "EURJPY=X", "name": "EUR / JPY"}, {"symbol": "GBPJPY=X", "name": "GBP / JPY"}
    ],
    "commodities": [
        {"symbol": "GC=F", "name": "Or (Gold)"}, {"symbol": "SI=F", "name": "Argent (Silver)"},
        {"symbol": "CL=F", "name": "Pétrole Brut WTI"}, {"symbol": "BZ=F", "name": "Pétrole Brent"},
        {"symbol": "HG=F", "name": "Cuivre (Copper)"}, {"symbol": "NG=F", "name": "Gaz Naturel"},
        {"symbol": "PL=F", "name": "Platine (Platinum)"}
    ],
    "indices": [
        {"symbol": "URTH", "name": "MSCI World Index (Monde)"},
        {"symbol": "ACWI", "name": "MSCI ACWI (Monde + Émergents)"},
        {"symbol": "^GSPC", "name": "S&P 500 (US)"}, {"symbol": "^IXIC", "name": "Nasdaq Composite"},
        {"symbol": "^DJI", "name": "Dow Jones 30"}, {"symbol": "^FCHI", "name": "CAC 40 (France)"},
        {"symbol": "^GDAXI", "name": "DAX 40 (Allemagne)"}, {"symbol": "^N225", "name": "Nikkei 225 (Japon)"},
        {"symbol": "^FTSE", "name": "FTSE 100 (Londres)"}
    ],
    "etf": [
        {"symbol": "URTH", "name": "iShares MSCI World ETF"},
        {"symbol": "ACWI", "name": "iShares MSCI ACWI ETF"},
        {"symbol": "VT", "name": "Vanguard Total World Stock"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"}, {"symbol": "QQQ", "name": "Invesco QQQ (Nasdaq)"},
        {"symbol": "SMH", "name": "VanEck Semiconductor ETF"}, {"symbol": "GLD", "name": "SPDR Gold Shares"},
        {"symbol": "SLV", "name": "iShares Silver Trust"}, {"symbol": "TLT", "name": "iShares 20+ Year Treasury"},
        {"symbol": "IWM", "name": "iShares Russell 2000"}, {"symbol": "SOXX", "name": "iShares Semiconductor"}
    ]
}

class UnifiedMarketProvider:
    @staticmethod
    def get_market_assets(category: str, limit: int = 50) -> List[Dict[str, str]]:
        assets = MARKET_CATALOG.get(category, [])
        return assets[:limit]

    @staticmethod
    def fetch_and_analyze(symbol: str, timeframe: str = '1wk', period: str = '10y') -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=timeframe)
            if df.empty or len(df) < 25:
                return {}

            # Normalisation systématique des colonnes
            df['Close'] = df['Close'] if 'Close' in df.columns else df['close']
            df['Open'] = df['Open'] if 'Open' in df.columns else df['open']
            df['High'] = df['High'] if 'High' in df.columns else df['high']
            df['Low'] = df['Low'] if 'Low' in df.columns else df['low']
            df['close'] = df['Close']

            # Moyennes Mobiles Simples (SMA)
            df['ma5'] = TechnicalIndicators.calculate_sma(df['Close'], window=5)
            df['ma20'] = TechnicalIndicators.calculate_sma(df['Close'], window=20)
            df['ma80'] = TechnicalIndicators.calculate_sma(df['Close'], window=80)
            df['ma320'] = TechnicalIndicators.calculate_sma(df['Close'], window=320)
            df['rsi21'] = TechnicalIndicators.calculate_rsi(df['Close'], period=21)

            # Paolo BBW (80 et 320)
            bbw80_res = TechnicalIndicators.calculate_paolo_bbw_compression(df, period=80, dev=2.0, lookback=52)
            bbw320_res = TechnicalIndicators.calculate_paolo_bbw_compression(df, period=320, dev=2.0, lookback=52)
            df['bbw80'] = bbw80_res['bbw_series']
            df['bbw80_min'] = bbw80_res['min_lookback_series']
            df['bbw320'] = bbw320_res['bbw_series']
            df['bbw320_min'] = bbw320_res['min_lookback_series']

            regime, state = TechnicalIndicators.evaluate_regime_and_state(df)
            rsi21_strat = TechnicalIndicators.evaluate_rsi21_polarity_strategy(df)
            rsi_sma20_320_strat = TechnicalIndicators.evaluate_rsi21_sma20_320_strategy(df)

            last_close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else last_close
            change_pct = ((last_close - prev_close) / prev_close) * 100

            ath_price = float(df['High'].max())
            dist_ath_pct = ((last_close - ath_price) / ath_price) * 100 if ath_price > 0 else 0.0

            mcap = None
            try:
                mcap = ticker.fast_info.market_cap
            except Exception:
                mcap = None

            vol_val = 0.0
            if 'Volume' in df.columns and len(df['Volume']) > 0:
                v = df['Volume'].iloc[-1]
                if pd.notna(v) and v > 0:
                    vol_val = float(v) * last_close

            return {
                "symbol": symbol,
                "price": round(last_close, 4 if ("USD" in symbol or "=X" in symbol) else 2),
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
                "volume": fmt_currency(vol_val),
                "market_cap": fmt_currency(mcap) if mcap else "N/A",
                "ath_price": round(ath_price, 2),
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
        except Exception:
            return {}
