import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

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
    def calculate_paolo_bbw_compression(df: pd.DataFrame, period: int = 80, dev: float = 2.0, lookback: int = 52) -> Dict[str, Any]:
        close = df['Close']
        middle = df['ma80'] if 'ma80' in df.columns else close.ewm(span=period, adjust=False).mean()
        rolling_std = close.rolling(window=period, min_periods=25).std().fillna(close.std())
        upper = middle + (dev * rolling_std)
        lower = middle - (dev * rolling_std)
        bbw_series = ((upper - lower) / middle.replace(0, 1e-9)) * 100.0
        bbw_series = bbw_series.fillna(0.0)
        min_lookback_series = bbw_series.rolling(window=lookback, min_periods=15).min().fillna(bbw_series)

        last_bbw = float(bbw_series.iloc[-1])
        last_min = float(min_lookback_series.iloc[-1])
        is_squeeze = (last_bbw <= last_min * 1.08) or (last_bbw <= last_min)
        prev_bbw = float(bbw_series.iloc[-2]) if len(bbw_series) > 1 else last_bbw
        is_expansion = (last_bbw > prev_bbw * 1.15) and not is_squeeze
        status = "bbw_squeeze" if is_squeeze else ("bbw_expansion" if is_expansion else "bbw_normal")

        return {
            "bbw_series": bbw_series,
            "min_lookback_series": min_lookback_series,
            "current_bbw": round(last_bbw, 2),
            "min_bbw": round(last_min, 2),
            "is_squeeze": is_squeeze,
            "status": status
        }

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

    @staticmethod
    def evaluate_rsi21_polarity_strategy(df: pd.DataFrame) -> Dict[str, Any]:
        """
        STRATÉGIE RSI 21 (PAOLO BASSO) :
        - Polarité acheteuse validée après cycle Survente (<=30) -> Surachat (>=70)
        - Trade 1 : SL = Creux lors du RSI <= 30
        - Pour autoriser Trade N+1 : Le RSI DOIT impérativement retourner en Surachat (>=70)
        - Puis pullback sous 50 (RSI < 50)
        - Entrée sur croisement MM5 > MM20
        - SL du Trade N = Creux du Trade N-1
        - TP1 = 1:1, objectif retour >= 70
        """
        polarity = False
        has_touched_oversold = False
        oversold_lowest_low = None
        
        current_pullback_lowest = None
        pullback_in_progress = False
        returned_to_overbought = False

        previous_trade_low = None  # Mémorise le creux du trade précédent pour le SL en cascade
        trade_count = 0
        last_signal_event = None
        active_trade = None

        n = len(df)
        for i in range(n):
            rsi = float(df['rsi21'].iloc[i])
            low = float(df['Low'].iloc[i])
            close = float(df['Close'].iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            prev_m5 = float(df['ma5'].iloc[i-1]) if i > 0 else m5
            prev_m20 = float(df['ma20'].iloc[i-1]) if i > 0 else m20

            # 1. Détection Survente initiale (Cycle 0)
            if rsi <= 30:
                has_touched_oversold = True
                oversold_lowest_low = low if oversold_lowest_low is None else min(oversold_lowest_low, low)

            # 2. Validation Polarité Acheteuse (Survente -> Surachat)
            if has_touched_oversold and rsi >= 70:
                polarity = True
                has_touched_oversold = False
                returned_to_overbought = True  # Autorise le Trade 1

            if polarity:
                # 3. Vérification du retour en surachat requis pour les trades suivants
                if trade_count >= 1 and rsi >= 70:
                    returned_to_overbought = True

                # 4. Phase de Pullback sous 50 (autorisée seulement si le retour à 70 a eu lieu)
                if returned_to_overbought and rsi < 50:
                    if not pullback_in_progress:
                        pullback_in_progress = True
                        current_pullback_lowest = low
                    else:
                        current_pullback_lowest = min(current_pullback_lowest, low)

                # 5. Déclencheur : Croisement MM5 > MM20
                is_crossover = (prev_m5 <= prev_m20 and m5 > m20)
                if pullback_in_progress and is_crossover:
                    trade_count += 1
                    
                    if trade_count == 1:
                        # Règle Trade 1 : SL au plus bas de la survente originelle
                        sl = oversold_lowest_low if oversold_lowest_low is not None else low
                        t_type = "Trade 1 (Post-Survente)"
                    else:
                        # Règle Trade 2+ : SL = Creux du Trade N-1 !
                        sl = previous_trade_low if previous_trade_low is not None else (current_pullback_lowest if current_pullback_lowest is not None else low)
                        t_type = f"Trade {trade_count} (SL = Creux Trade {trade_count-1})"

                    risk = close - sl
                    tp1 = close + risk if risk > 0 else close * 1.05

                    # Enregistrement du creux du trade actuel qui deviendra le SL du prochain trade !
                    previous_trade_low = current_pullback_lowest if current_pullback_lowest is not None else low
                    
                    # Réinitialisation des verrous
                    pullback_in_progress = False
                    current_pullback_lowest = None
                    returned_to_overbought = False  # DOIT impérativement remonter à 70 avant le trade suivant !

                    active_trade = {
                        "entry": close,
                        "sl": sl,
                        "tp1": tp1,
                        "trade_type": t_type
                    }

                    if i == n - 1:
                        last_signal_event = "signal_buy_fresh"

        # Diagnostic temps réel sur la dernière bougie
        last_rsi = float(df['rsi21'].iloc[-1])
        if last_signal_event == "signal_buy_fresh" and active_trade:
            state = "STATE_FRESH_BUY"
        elif polarity and pullback_in_progress:
            state = "STATE_PULLBACK_50"
        elif polarity and returned_to_overbought:
            state = "STATE_OVERBOUGHT_READY"
        elif polarity:
            state = "STATE_BULLISH_TREND"
        else:
            state = "STATE_WAIT_POLARITY"

        return {
            "polarity": "POLARITY_BULL" if polarity else "POLARITY_WAIT",
            "state": state,
            "trade_count": trade_count,
            "sl_price": round(active_trade['sl'], 4) if active_trade else None,
            "tp1_price": round(active_trade['tp1'], 4) if active_trade else None,
            "trade_type": active_trade['trade_type'] if active_trade else ""
        }
