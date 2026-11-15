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
        {"symbol": "JPM", "name": "JPMorgan Chase"},
        {"symbol": "LLY", "name": "Eli Lilly"},
        {"symbol": "V", "name": "Visa"},
        {"symbol": "WMT", "name": "Walmart"},
        {"symbol": "XOM", "name": "ExxonMobil"},
        {"symbol": "MA", "name": "Mastercard"},
        {"symbol": "ORCL", "name": "Oracle"},
        {"symbol": "COST", "name": "Costco"},
        {"symbol": "HD", "name": "Home Depot"},
        {"symbol": "PG", "name": "Procter & Gamble"},
        {"symbol": "NFLX", "name": "Netflix"},
        {"symbol": "BAC", "name": "Bank of America"},
        {"symbol": "CRM", "name": "Salesforce"},
        {"symbol": "ABBV", "name": "AbbVie"},
        {"symbol": "CVX", "name": "Chevron"},
        {"symbol": "KO", "name": "Coca-Cola"},
        {"symbol": "AMD", "name": "AMD"},
        {"symbol": "PEP", "name": "PepsiCo"},
        {"symbol": "LIN", "name": "Linde"},
        {"symbol": "TMO", "name": "Thermo Fisher"},
        {"symbol": "ADBE", "name": "Adobe"},
        {"symbol": "MRK", "name": "Merck"},
        {"symbol": "PLTR", "name": "Palantir Technologies"},
        {"symbol": "DIS", "name": "Walt Disney"},
        {"symbol": "QCOM", "name": "Qualcomm"},
        {"symbol": "INTU", "name": "Intuit"},
        {"symbol": "IBM", "name": "IBM"},
        {"symbol": "CAT", "name": "Caterpillar"},
        {"symbol": "TXN", "name": "Texas Instruments"},
        {"symbol": "NOW", "name": "ServiceNow"},
        {"symbol": "GE", "name": "General Electric"},
        {"symbol": "UBER", "name": "Uber Technologies"},
        {"symbol": "AMAT", "name": "Applied Materials"},
        {"symbol": "VZ", "name": "Verizon"},
        {"symbol": "PFE", "name": "Pfizer"},
        {"symbol": "UNH", "name": "UnitedHealth"},
        {"symbol": "INTC", "name": "Intel"},
        {"symbol": "BA", "name": "Boeing"},
        {"symbol": "NKE", "name": "Nike"},
        {"symbol": "SBUX", "name": "Starbucks"},
        {"symbol": "COIN", "name": "Coinbase"}
    ],
    "forex": [
        {"symbol": "EURUSD=X", "name": "EUR / USD"},
        {"symbol": "GBPUSD=X", "name": "GBP / USD"},
        {"symbol": "USDJPY=X", "name": "USD / JPY"},
        {"symbol": "USDCHF=X", "name": "USD / CHF"},
        {"symbol": "AUDUSD=X", "name": "AUD / USD"},
        {"symbol": "USDCAD=X", "name": "USD / CAD"},
        {"symbol": "NZDUSD=X", "name": "NZD / USD"},
        {"symbol": "EURGBP=X", "name": "EUR / GBP"},
        {"symbol": "EURJPY=X", "name": "EUR / JPY"},
        {"symbol": "GBPJPY=X", "name": "GBP / JPY"}
    ],
    "commodities": [
        {"symbol": "GC=F", "name": "Or (Gold)"},
        {"symbol": "SI=F", "name": "Argent (Silver)"},
        {"symbol": "CL=F", "name": "Pétrole Brut WTI"},
        {"symbol": "BZ=F", "name": "Pétrole Brent"},
        {"symbol": "HG=F", "name": "Cuivre (Copper)"},
        {"symbol": "NG=F", "name": "Gaz Naturel"},
        {"symbol": "PL=F", "name": "Platine (Platinum)"}
    ],
    "indices": [
        {"symbol": "^GSPC", "name": "S&P 500 (US)"},
        {"symbol": "^IXIC", "name": "Nasdaq Composite"},
        {"symbol": "^DJI", "name": "Dow Jones 30"},
        {"symbol": "^FCHI", "name": "CAC 40 (France)"},
        {"symbol": "^GDAXI", "name": "DAX 40 (Allemagne)"},
        {"symbol": "^N225", "name": "Nikkei 225 (Japon)"},
        {"symbol": "^FTSE", "name": "FTSE 100 (Londres)"}
    ],
    "etf": [
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ (Nasdaq 100)"},
        {"symbol": "SMH", "name": "VanEck Semiconductor ETF"},
        {"symbol": "GLD", "name": "SPDR Gold Shares"},
        {"symbol": "SLV", "name": "iShares Silver Trust"},
        {"symbol": "TLT", "name": "iShares 20+ Year Treasury"},
        {"symbol": "IWM", "name": "iShares Russell 2000"},
        {"symbol": "ARKK", "name": "ARK Innovation ETF"},
        {"symbol": "SOXX", "name": "iShares Semiconductor ETF"}
    ]
}

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

            mcap = None
            try:
                mcap = ticker.fast_info.market_cap
            except Exception:
                mcap = None

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
