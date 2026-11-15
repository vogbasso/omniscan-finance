import pandas as pd
from typing import Tuple

class TechnicalIndicators:
    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 21) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def evaluate_rsi_zone(rsi_val: float) -> str:
        if rsi_val >= 70:
            return "rsi_overbought"
        elif rsi_val <= 30:
            return "rsi_oversold"
        elif 45 <= rsi_val <= 55:
            return "rsi_neutral"
        elif rsi_val > 55:
            return "rsi_bullish"
        else:
            return "rsi_bearish"

    @staticmethod
    def evaluate_regime_and_state(df: pd.DataFrame) -> Tuple[str, str]:
        regime = "regime_bull" if df['ma20'].iloc[0] > df['ma80'].iloc[0] else "regime_bear"
        is_fresh_signal = False
        last_signal = None

        for i in range(len(df)):
            p = float(df['close'].iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            m80 = float(df['ma80'].iloc[i])

            if m20 > m80 and (p < m5 and p < m20 and p < m80):
                if regime != "regime_bear":
                    regime = "regime_bear"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_sell"

            elif m20 < m80 and (p > m5 and p > m20 and p > m80):
                if regime != "regime_bull":
                    regime = "regime_bull"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_buy"

        if is_fresh_signal and last_signal:
            return regime, last_signal

        last_p = float(df['close'].iloc[-1])
        last_m5 = float(df['ma5'].iloc[-1])
        last_m20 = float(df['ma20'].iloc[-1])
        last_m80 = float(df['ma80'].iloc[-1])

        if last_m5 > last_m20 > last_m80:
            state = "state_strong_bull"
        elif last_m5 < last_m20 < last_m80:
            state = "state_strong_bear"
        elif last_m20 > last_m80 and (last_m80 < last_m5 < last_m20):
            state = "state_slowdown_bull"
        elif last_m20 < last_m80 and (last_m20 < last_m5 < last_m80):
            state = "state_slowdown_bear"
        else:
            state = "state_consolidation"

        return regime, state
