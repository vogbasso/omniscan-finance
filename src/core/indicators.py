import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List

class TechnicalIndicators:
    @staticmethod
    def calculate_sma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window, min_periods=1).mean()

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
        close = df['Close'] if 'Close' in df.columns else df['close']
        ma_col = f"ma{period}"
        middle = df[ma_col] if ma_col in df.columns else close.rolling(window=period, min_periods=1).mean()
        rolling_std = close.rolling(window=min(period, len(close)), min_periods=15).std().fillna(close.std())
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
        regime = None
        is_fresh_signal = False
        last_signal = None
        close_col = df['Close'] if 'Close' in df.columns else df['close']

        for i in range(len(df)):
            p = float(close_col.iloc[i])
            m20 = float(df['ma20'].iloc[i])
            m80 = float(df['ma80'].iloc[i])

            cloud_top = max(m20, m80)
            cloud_bottom = min(m20, m80)

            if p > cloud_top:
                if regime is None:
                    regime = "regime_bull"
                elif regime != "regime_bull":
                    regime = "regime_bull"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_buy"
            elif p < cloud_bottom:
                if regime is None:
                    regime = "regime_bear"
                elif regime != "regime_bear":
                    regime = "regime_bear"
                    if i == len(df) - 1:
                        is_fresh_signal = True
                        last_signal = "state_new_sell"

        if regime is None:
            regime = "regime_bear"

        if is_fresh_signal and last_signal:
            return regime, last_signal

        last_p = float(close_col.iloc[-1])
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
        polarity = "POLARITY_BEAR"
        for r in df['rsi21']:
            if r >= 70:
                polarity = "POLARITY_BULL"
                break
            elif r <= 30:
                polarity = "POLARITY_BEAR"
                break

        oversold_lowest_low = None
        current_pullback_lowest = None
        pullback_in_progress = False
        returned_to_overbought = False
        structural_lows_history: List[float] = []

        trade_count = 0
        last_signal_event = None
        active_trade = None
        trade_signals_history = []

        close_col = df['Close'] if 'Close' in df.columns else df['close']
        low_col = df['Low'] if 'Low' in df.columns else df['low']

        n = len(df)
        for i in range(n):
            rsi = float(df['rsi21'].iloc[i])
            prev_rsi = float(df['rsi21'].iloc[i-1]) if i > 0 else 50.0
            low = float(low_col.iloc[i])
            close = float(close_col.iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            prev_m5 = float(df['ma5'].iloc[i-1]) if i > 0 else m5
            prev_m20 = float(df['ma20'].iloc[i-1]) if i > 0 else m20

            if rsi >= 70:
                polarity = "POLARITY_BULL"
                returned_to_overbought = True
                if oversold_lowest_low is not None and not structural_lows_history:
                    structural_lows_history = [oversold_lowest_low]
            elif rsi <= 30:
                polarity = "POLARITY_BEAR"
                trade_count = 0
                pullback_in_progress = False
                returned_to_overbought = False
                structural_lows_history.clear()
                if oversold_lowest_low is None or prev_rsi > 30:
                    oversold_lowest_low = low
                else:
                    oversold_lowest_low = min(oversold_lowest_low, low)

            if polarity == "POLARITY_BULL":
                if returned_to_overbought and rsi < 50:
                    if not pullback_in_progress:
                        pullback_in_progress = True
                        current_pullback_lowest = low
                    else:
                        current_pullback_lowest = min(current_pullback_lowest, low)

                is_crossover = (prev_m5 <= prev_m20 and m5 > m20)
                if pullback_in_progress and is_crossover:
                    trade_count += 1
                    entry_price = close
                    
                    if trade_count == 1:
                        sl = oversold_lowest_low if (oversold_lowest_low is not None and oversold_lowest_low < entry_price) else (current_pullback_lowest if current_pullback_lowest and current_pullback_lowest < entry_price else low * 0.98)
                        t_type = "T1 (Post-Survente)"
                    else:
                        sl = None
                        for past_low in reversed(structural_lows_history):
                            if past_low < entry_price:
                                sl = past_low
                                break
                        if sl is None:
                            sl = current_pullback_lowest if (current_pullback_lowest and current_pullback_lowest < entry_price) else (low * 0.97)
                        t_type = f"T{trade_count} (SL Adaptatif)"

                    risk = entry_price - sl
                    tp1 = entry_price + risk if risk > 0 else entry_price * 1.05

                    if current_pullback_lowest is not None:
                        structural_lows_history.append(current_pullback_lowest)
                    else:
                        structural_lows_history.append(low)

                    pullback_in_progress = False
                    current_pullback_lowest = None
                    returned_to_overbought = False

                    trade_signals_history.append({
                        "date": df.index[i],
                        "price": entry_price,
                        "sl": sl,
                        "tp1": tp1,
                        "label": f"T{trade_count}"
                    })

                    active_trade = {
                        "entry": entry_price,
                        "sl": sl,
                        "tp1": tp1,
                        "trade_type": t_type
                    }

                    if i == n - 1:
                        last_signal_event = "signal_buy_fresh"

        last_rsi = float(df['rsi21'].iloc[-1])
        if last_signal_event == "signal_buy_fresh" and active_trade:
            state = "STATE_FRESH_BUY"
        elif polarity == "POLARITY_BULL":
            if last_rsi >= 70:
                state = "STATE_OVERBOUGHT_IMPULSE"
            elif last_rsi < 50:
                state = "STATE_PULLBACK_50"
            else:
                state = "STATE_BULLISH_TREND"
        else:
            state = "STATE_BEARISH_REGIME"

        return {
            "polarity": polarity,
            "state": state,
            "trade_count": trade_count,
            "sl_price": round(active_trade['sl'], 4) if active_trade else None,
            "tp1_price": round(active_trade['tp1'], 4) if active_trade else None,
            "trade_type": active_trade['trade_type'] if active_trade else "",
            "trade_signals_history": trade_signals_history
        }

    @staticmethod
    def evaluate_rsi21_sma20_320_strategy(df: pd.DataFrame) -> Dict[str, Any]:
        """
        STRATÉGIE PAR DÉFAUT PAOLO BASSO :
        - Tendance Macro : SMA 20 vs SMA 320 (Long Only)
        - TRADE 1 (OBLIGATOIRE) : En tendance baissière (20 < 320), ENTRÉE DIRECTE dès que RSI 21 touche >= 70 !
        - Stop Loss T1 : Plus bas absolu enregistré pendant toute la phase de vente (20 < 320)
        - Sorties : TP1 50% à 1:1, TP2 35% à 1:3, Trailing 15% jusqu'à repasse sous 320
        - Confirmation ultérieure : Attente que SMA 20 croise au-dessus de SMA 320
        - Respirations ultérieures (Optionnelles) : Confirmées par retour du RSI < 50
        """
        close_col = df['Close'] if 'Close' in df.columns else df['close']
        low_col = df['Low'] if 'Low' in df.columns else df['low']

        n = len(df)
        in_bear_phase = False
        bear_lowest_low = None
        has_entered_trade1 = False
        active_trade = None
        trade_signals_history = []
        last_signal_event = None

        for i in range(n):
            close = float(close_col.iloc[i])
            low = float(low_col.iloc[i])
            m5 = float(df['ma5'].iloc[i])
            m20 = float(df['ma20'].iloc[i])
            m320 = float(df['ma320'].iloc[i])
            prev_m5 = float(df['ma5'].iloc[i-1]) if i > 0 else m5
            prev_m20 = float(df['ma20'].iloc[i-1]) if i > 0 else m20
            rsi = float(df['rsi21'].iloc[i])

            is_macro_bear = m20 < m320
            is_macro_bull = m20 >= m320

            if is_macro_bear:
                if not in_bear_phase:
                    in_bear_phase = True
                    bear_lowest_low = low
                    has_entered_trade1 = False
                else:
                    bear_lowest_low = min(bear_lowest_low, low)

                # ÉTAPE 1 : ENTRÉE DIRECTE & OBLIGATOIRE DÈS SURACHAT RSI >= 70 !
                if rsi >= 70 and not has_entered_trade1:
                    has_entered_trade1 = True
                    entry_price = close
                    sl_price = bear_lowest_low if (bear_lowest_low is not None and bear_lowest_low < entry_price) else low * 0.95
                    risk = entry_price - sl_price
                    tp1 = entry_price + (1.0 * risk)
                    tp2 = entry_price + (3.0 * risk)

                    active_trade = {
                        "entry": entry_price,
                        "sl": sl_price,
                        "tp1": tp1,
                        "tp2": tp2,
                        "status": "WAIT_CONFIRMATION_20_320",
                        "date": df.index[i],
                        "type": "T1 OBLIGATOIRE (RSI >= 70 sous 320)"
                    }

                    trade_signals_history.append({
                        "date": df.index[i],
                        "price": entry_price,
                        "sl": sl_price,
                        "tp1": tp1,
                        "tp2": tp2,
                        "label": "T1 OBLIGATOIRE"
                    })

                    if i == n - 1:
                        last_signal_event = "signal_t1_fresh"

            elif is_macro_bull:
                in_bear_phase = False
                if active_trade and active_trade["status"] == "WAIT_CONFIRMATION_20_320":
                    active_trade["status"] = "TREND_CONFIRMED_BULL"

        # Diagnostic temps réel sur la dernière bougie
        last_m20 = float(df['ma20'].iloc[-1])
        last_m320 = float(df['ma320'].iloc[-1])
        last_rsi = float(df['rsi21'].iloc[-1])
        macro_trend = "BULL" if last_m20 >= last_m320 else "BEAR"

        # Statuts du screener
        if last_signal_event == "signal_t1_fresh":
            state = "STATE_FRESH_T1_BUY"
        elif active_trade and active_trade["status"] == "TREND_CONFIRMED_BULL" and macro_trend == "BULL":
            state = "STATE_TREND_CONFIRMED"
        elif active_trade and active_trade["status"] == "WAIT_CONFIRMATION_20_320" and macro_trend == "BEAR":
            if last_rsi < 50:
                state = "STATE_TRADE1_PULLBACK"    # Le Trade 1 est actif et respire sous 50 (pullback optionnel)
            else:
                state = "STATE_TRADE1_HOLDING"     # Le Trade 1 progresse vers le crossover 20 > 320
        elif macro_trend == "BEAR":
            state = "STATE_BEAR_WATCHING"
        else:
            state = "STATE_BULL_ACTIVE"

        return {
            "macro_trend": macro_trend,
            "state": state,
            "active_trade": active_trade,
            "entry_price": round(active_trade["entry"], 4) if active_trade else None,
            "sl_price": round(active_trade["sl"], 4) if active_trade else None,
            "tp1_price": round(active_trade["tp1"], 4) if active_trade else None,
            "tp2_price": round(active_trade["tp2"], 4) if active_trade else None,
            "bear_lowest_low": round(bear_lowest_low, 4) if bear_lowest_low else None,
            "trade_signals_history": trade_signals_history
        }
