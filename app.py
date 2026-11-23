import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

from src.providers.crypto import BinanceCryptoProvider
from src.providers.markets import UnifiedMarketProvider
from src.core.indicators import TechnicalIndicators

st.set_page_config(
    page_title="OmniScan Finance - Screener RSI 21 & SMA 20/320",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

st.sidebar.title("🌐 OmniScan Finance")
st.sidebar.caption("Architecte & Auteur : **Vogel Paolo BASSO**")

lang = st.sidebar.selectbox("Langue / Language", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"
t = load_locale(lang_code)

st.sidebar.markdown("---")

# SÉLECTEUR DE MÉTHODE D'ANALYSE (OPTION 1 PAR DÉFAUT)
strategy_choice = st.sidebar.radio(
    "Méthode d'Analyse" if lang_code == "fr" else "Strategy",
    options=[
        "🌟 Reversal Impulsion (RSI 21 / SMA 20-320) [Défaut]",
        "🎯 RSI 21 / Pullback 50 & MM 5-20",
        "📊 Triple MM 5 / 20 / 80 (Cloud 20/80)"
    ],
    index=0
)
is_impulse_strategy = "Reversal Impulsion" in strategy_choice
is_pullback50_strategy = "Pullback 50" in strategy_choice
is_cloud_strategy = "Triple MM" in strategy_choice

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ " + ("Configuration du Scan" if lang_code == "fr" else "Scan Settings"))

market_options = {
    "crypto": t["menu_crypto"],
    "retirement": t.get("menu_retirement", "💼 Mon Plan Retraite"),
    "stocks": t["menu_stocks"],
    "forex": t["menu_forex"],
    "commodities": t["menu_commodities"],
    "indices": t["menu_indices"],
    "etf": t["menu_etf"]
}

selected_category = st.sidebar.selectbox(
    "Choisir la catégorie" if lang_code == "fr" else "Select category",
    options=list(market_options.keys()),
    format_func=lambda x: market_options[x]
)

scan_limit = st.sidebar.slider(
    "Nombre d'actifs" if lang_code == "fr" else "Number of assets",
    min_value=10, max_value=100, value=25, step=5
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 " + ("Recherche Ciblée" if lang_code == "fr" else "Targeted Search"))
custom_search = st.sidebar.text_input("Ticker personnalisé (ex: BTC/USDT, NVDA)", value="").strip().upper()

timeframe_display = "Hebdomadaire (Weekly - 1w)" if lang_code == "fr" else "Weekly (1w)"
st.sidebar.info(f"⏱️ **Timeframe** : {timeframe_display}")

# En-tête
if is_impulse_strategy:
    st.title("🌟 OmniScan Finance — Stratégie Reversal Impulsion (RSI 21 / SMA 20-320)")
    st.caption("Surachat RSI 21 (>= 70) sous SMA 320 -> Pullback sous 50 -> Entrée Croisement SMA 5 > SMA 20 • SL Bas Bear • TP1 (50% @ 1:1) • TP2 (35% @ 1:3) • Trailing 15%")
elif is_pullback50_strategy:
    st.title("🎯 OmniScan Finance — Stratégie RSI 21 / MM 5-20 & Pullback 50")
    st.caption("Polarité par transition 30/70 • Pullback sous 50 • Crossover MM 5/20 • Long Only")
else:
    st.title("📊 OmniScan Finance — Stratégie Triple MM 5 / 20 / 80")
    st.caption("Cloud SMA 20 / SMA 80 • Mémoire de Régime • Compression Paolo BBW (80)")

@st.cache_data(ttl=300, show_spinner=False)
def get_scanned_data(category: str, limit: int):
    results = []
    charts = {}
    if category == "crypto":
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=limit)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe="1w", limit=500, meta_info=p)
            if data:
                data["name"] = p.get("name", p['symbol'].split('/')[0])
                charts[data["symbol"]] = data.pop("df", None)
                results.append(data)
    else:
        assets = UnifiedMarketProvider.get_market_assets(category, limit=limit)
        for item in assets:
            data = UnifiedMarketProvider.fetch_and_analyze(item["symbol"], timeframe="1wk")
            if data:
                data["name"] = item["name"]
                charts[item["symbol"]] = data.pop("df", None)
                results.append(data)
    return results, charts

with st.spinner("Analyse quantitative des flux..." if lang_code == "fr" else "Running scan..."):
    results, charts_cache = get_scanned_data(selected_category, scan_limit)

if results:
    st.markdown("---")
    
    # RADARS D'ALERTE
    if is_impulse_strategy:
        fresh_impulse_buys = [r for r in results if r.get("impulse_state") == "STATE_FRESH_BUY"]
        pullback_ready = [r for r in results if r.get("impulse_state") == "STATE_PULLBACK_50_READY"]

        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT FRAIS (CROISEMENT SMA 5 > SMA 20 APRÈS PULLBACK < 50)")
        if fresh_impulse_buys:
            st.success(f"🔥 ALERTE ACHAT VALIDÉE : {len(fresh_impulse_buys)} signal(ux) d'entrée validé(s) !")
            cols1 = st.columns(min(len(fresh_impulse_buys), 4))
            for idx, sig in enumerate(fresh_impulse_buys[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix Entrée** : `${sig['price']}`")
                    st.write(f"**Stop Loss (Bas Bear)** : `${sig.get('impulse_sl')}`")
                    st.write(f"**TP1 (50% @ 1:1)** : `${sig.get('impulse_tp1')}`")
                    st.write(f"**TP2 (35% @ 1:3)** : `${sig.get('impulse_tp2')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais déclenché cette semaine sur cette sélection.")

        st.markdown("---")
        st.subheader("🔭 RADAR 2 : ZONE DE VEILLE (PULLBACK SOUS 50 EN COURS — ATTENTE CROISEMENT SMA 5 > 20)")
        if pullback_ready:
            st.warning(f"👀 {len(pullback_ready)} actif(s) ayant validé l'impulsion >= 70 et respirant sous 50 (À l'affût du croisement SMA 5 > 20) !")
            cols2 = st.columns(min(len(pullback_ready), 4))
            for idx, pr in enumerate(pullback_ready[:4]):
                with cols2[idx]:
                    st.markdown(f"#### **{pr['name']}** ({pr['symbol']})")
                    st.write(f"**Prix Actuel** : `${pr['price']}`")
                    st.write(f"**RSI (21)** : `{pr.get('rsi')} (< 50)`")
                    st.write(f"**SMA 5** : `${round(pr.get('df_m5', pr['price']), 2)}` | **SMA 20** : `${round(pr.get('df_m20', pr['price']), 2)}`")
        else:
            st.info("ℹ️ Aucun actif actuellement en zone de pullback sous 50 après impulsion.")
        if pullback_ready:
            st.warning(f"👀 {len(pullback_ready)} actif(s) entrés sur impulsion en route vers la confirmation SMA 20 > 320 !")
            cols2 = st.columns(min(len(pullback_ready), 4))
            for idx, pr in enumerate(pullback_ready[:4]):
                with cols2[idx]:
                    st.markdown(f"#### **{wc['name']}** ({wc['symbol']})")
                    st.write(f"**Prix Actuel** : `${wc['price']}`")
                    st.write(f"**SMA 20** : `${round(wc.get('df_m20', wc['price']), 2)}` | **SMA 320** : `${round(wc.get('df_m320', wc['price']), 2)}`")
                    st.write(f"**Stop Loss** : `${wc.get('impulse_sl')}`")
                    st.write(f"**TP1 (1:1)** : `${wc.get('impulse_tp1')}`")
        else:
            st.info("ℹ️ Aucune position en attente de confirmation 20 > 320.")

    elif is_pullback50_strategy:
        fresh_buys = [r for r in results if r.get("rsi_state") == "STATE_FRESH_BUY"]
        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT (PULLBACK < 50)")
        if fresh_buys:
            st.success(f"🔥 {len(fresh_buys)} signal(ux) validé(s) !")
            cols1 = st.columns(min(len(fresh_buys), 4))
            for idx, sig in enumerate(fresh_buys[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
                    st.write(f"**SL** : `${sig.get('rsi_sl')}` | **TP1** : `${sig.get('rsi_tp1')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais Pullback 50 cette semaine.")
    else:
        fresh_signals = [r for r in results if r.get("state") == "state_new_buy"]
        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT (CLOUD 20/80)")
        if fresh_signals:
            st.success(f"🔥 {len(fresh_signals)} signal(ux) frais détecté(s) !")
            cols1 = st.columns(min(len(fresh_signals), 4))
            for idx, sig in enumerate(fresh_signals[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais Cloud 20/80 cette semaine.")

    # Synthèse générale
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Actifs Scannés", len(results))
    if is_impulse_strategy:
        bull_count = sum(1 for r in results if r.get("macro_trend") == "BULL")
        k2.metric("🟢 Macro Haussière (20 > 320)", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
        bear_count = len(results) - bull_count
        k3.metric("🔴 Macro Baissière (20 < 320)", f"{bear_count} ({round(bear_count/len(results)*100)}%)")
    else:
        bull_count = sum(1 for r in results if (r.get("rsi_polarity") == "POLARITY_BULL" if is_pullback50_strategy else r.get("regime") == "regime_bull"))
        k2.metric("🟢 Tendance Acheteuse", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
        k3.metric("RSI Moyen", round(sum(r.get("rsi", 50) for r in results) / len(results), 1))
    
    squeeze_count = sum(1 for r in results if r.get("bbw320_squeeze", r.get("bbw_squeeze")))
    k4.metric("⚡ Squeeze Paolo BBW", squeeze_count)

    # TABLEAU DE DONNÉES SYNTHÉTIQUE
    st.markdown("---")
    st.subheader("📋 " + ("Résultats Détaillés du Marché" if lang_code == "fr" else "Detailed Market Results"))
    search_f = st.text_input("🔎 Filtrer dans la liste :", "").strip().upper()

    table_data = []
    for r in results:
        if search_f and search_f not in r["symbol"] and search_f not in r.get("name", "").upper():
            continue
        chg_val = r["change_pct"]
        chg_str = f"▲ +{chg_val:.2f}%" if chg_val > 0 else (f"▼ {chg_val:.2f}%" if chg_val < 0 else "  0.00%")
        rsi_val = r.get("rsi", 50.0)
        rsi_display = f"{rsi_val} | {t.get(r.get('rsi_zone', 'rsi_neutral'), '')}"

        bbw_val = r.get("bbw320", r.get("bbw", 0.0))
        is_sq = r.get("bbw320_squeeze", r.get("bbw_squeeze", False))
        bbw_str = f"⚡ {bbw_val:.1f}% (Squeeze)" if is_sq else f"{bbw_val:.1f}%"

        if is_impulse_strategy:
            macro_trend_label = "🟢 HAUSSIÈRE (20 > 320)" if r.get("macro_trend") == "BULL" else "🔴 BAISSIÈRE (20 < 320)"
            imp_state = r.get("impulse_state", "")
            if imp_state == "STATE_FRESH_BUY":
                statut_str = "🔥 ACHAT VALIDÉ (5 > 20)"
            elif imp_state == "STATE_PULLBACK_50_READY":
                statut_str = "⏳ PULLBACK < 50 (GUET 5/20)"
            elif imp_state == "STATE_OVERBOUGHT_IMPULSE":
                statut_str = "🚀 IMPULSION (RSI ≥ 70)"
            elif imp_state == "STATE_TREND_CONFIRMED":
                statut_str = "🚀 TENDANCE CONFIRMÉE (20 > 320)"
            elif imp_state == "STATE_WAIT_CONFIRMATION":
                statut_str = "⏳ EN COURS (ATTENTE 20 > 320)"
            elif imp_state == "STATE_BEAR_WATCHING":
                statut_str = "🔻 VEILLE (20 < 320)"
            else:
                statut_str = "↗️ FLUX HAUSSIER ACTIF"

            sl_str = f"${r.get('impulse_sl')}" if r.get('impulse_sl') else "—"
            tp1_str = f"${r.get('impulse_tp1')}" if r.get('impulse_tp1') else "—"
            tp2_str = f"${r.get('impulse_tp2')}" if r.get('impulse_tp2') else "—"

            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "Capitalisation": r.get("market_cap", "N/A"),
                "RSI (21)": rsi_display,
                "Tendance Macro": macro_trend_label,
                "Signal Détecté": statut_str,
                "Stop Loss (Bas Bear)": sl_str,
                "TP1 (50% @ 1:1)": tp1_str,
                "TP2 (35% @ 1:3)": tp2_str,
                "Trailing (15%)": "Jusqu'à 20 < 320",
                "Paolo BBW (320)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        elif is_pullback50_strategy:
            polarity_label = "🟢 ACHETEUSE" if r.get("rsi_polarity") == "POLARITY_BULL" else "🔴 VENDEUSE"
            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "Capitalisation": r.get("market_cap", "N/A"),
                "RSI (21)": rsi_display,
                "Polarité": polarity_label,
                "Signal Détecté": r.get("rsi_state", ""),
                "Stop Loss": f"${r.get('rsi_sl')}" if r.get('rsi_sl') else "—",
                "TP1 (1:1)": f"${r.get('rsi_tp1')}" if r.get('rsi_tp1') else "—",
                "Paolo BBW (320)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        else:
            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "Capitalisation": r.get("market_cap", "N/A"),
                "RSI (21)": rsi_display,
                t["col_regime"]: t.get(r["regime"], r["regime"]),
                "Signal Détecté": t.get(r["state"], r["state"]),
                "Paolo BBW (80)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        table_data.append(row)

    df_display = pd.DataFrame(table_data)

    def style_change(val):
        if "▲" in str(val):
            return "background-color: rgba(0, 230, 118, 0.18); color: #00e676; font-weight: bold;"
        elif "▼" in str(val):
            return "background-color: rgba(255, 82, 82, 0.18); color: #ff5252; font-weight: bold;"
        return ""

    def style_macro(val):
        if "HAUSSIÈRE" in str(val) or "ACHETEUSE" in str(val) or "ACHETEUR" in str(val):
            return "background-color: rgba(0, 230, 118, 0.15); color: #00e676; font-weight: bold; border-left: 3px solid #00e676;"
        elif "BAISSIÈRE" in str(val) or "VENDEUSE" in str(val) or "VENDEUR" in str(val):
            return "background-color: rgba(255, 82, 82, 0.15); color: #ff5252; font-weight: bold; border-left: 3px solid #ff5252;"
        return "color: #9e9e9e;"

    def style_signal(val):
        if "🔥" in str(val):
            return "background-color: rgba(0, 230, 118, 0.25); color: #00e676; font-weight: bold; border-left: 3px solid #00e676;"
        elif "🚀" in str(val):
            return "background-color: rgba(41, 98, 255, 0.25); color: #2962ff; font-weight: bold;"
        elif "⏳" in str(val):
            return "background-color: rgba(255, 171, 0, 0.2); color: #ffab00; font-weight: bold;"
        return ""

    def style_bbw(val):
        if "⚡" in str(val):
            return "background-color: rgba(30, 144, 255, 0.25); color: #1e90ff; font-weight: bold;"
        return ""

    styler = df_display.style
    try:
        col_macro = "Tendance Macro" if is_impulse_strategy else ("Polarité" if is_pullback50_strategy else t["col_regime"])
        col_bbw = "Paolo BBW (320)" if not is_cloud_strategy else "Paolo BBW (80)"
        styled_df = (
            styler.map(style_change, subset=[t["col_change"]])
            .map(style_macro, subset=[col_macro])
            .map(style_signal, subset=["Signal Détecté"])
            .map(style_bbw, subset=[col_bbw])
        )
        st.dataframe(styled_df, use_container_width=True, height=450)
    except Exception:
        st.dataframe(df_display, use_container_width=True, height=450)

    # 3. INSPECTEUR GRAPHIQUE INTERACTIF
    st.markdown("---")
    macro_name = "SMA 320" if not is_cloud_strategy else "SMA 80"
    st.subheader(f"📈 Inspecteur Technique : Chandeliers + SMA 20 + {macro_name} + RSI 21 + Niveaux TP/SL")
    selected_sym = st.selectbox("Sélectionnez un actif :", [r["symbol"] for r in results])
    df_chart = charts_cache.get(selected_sym)

    active_asset = next((x for x in results if x["symbol"] == selected_sym), None)
    trade_signals = []
    if active_asset:
        if is_impulse_strategy:
            trade_signals = active_asset.get("rsi_sma20_320_strat", {}).get("trade_signals_history", [])
        else:
            trade_signals = active_asset.get("trade_signals_history", [])

    if df_chart is not None and not df_chart.empty:
        if 'ma20' not in df_chart.columns:
            df_chart['ma20'] = TechnicalIndicators.calculate_sma(df_chart['Close'], window=20)
        if 'ma80' not in df_chart.columns:
            df_chart['ma80'] = TechnicalIndicators.calculate_sma(df_chart['Close'], window=80)
        if 'ma320' not in df_chart.columns:
            df_chart['ma320'] = TechnicalIndicators.calculate_sma(df_chart['Close'], window=320)

        active_macro_col = 'ma320' if not is_cloud_strategy else 'ma80'
        active_bbw_series = df_chart.get('bbw320', df_chart.get('bbw')) if not is_cloud_strategy else df_chart.get('bbw80', df_chart.get('bbw'))
        active_bbw_min = df_chart.get('bbw320_min', df_chart.get('bbw_min')) if not is_cloud_strategy else df_chart.get('bbw80_min', df_chart.get('bbw_min'))

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
            row_heights=[0.55, 0.23, 0.22],
            subplot_titles=(
                f"Chandeliers, SMA 20 & {macro_name} — {selected_sym}",
                "RSI (21) • Seuil Surachat 70 Déclencheur",
                f"Paolo BBW % ({macro_name}) & Seuil Compression"
            )
        )
        
        # Étage 1 : Chandeliers, SMA 5 (Visuel court terme), SMA 20 et Macro SMA
        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="Prix"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma5'], line=dict(color='#00d4ff', width=1.5), name='SMA 5 (Court terme)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma20'], line=dict(color='#ffaa00', width=2), name='SMA 20 (Intermédiaire)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart[active_macro_col], line=dict(color='#d000ff', width=2.5), name=macro_name), row=1, col=1)

        # Signaux d'entrée ▲
        if trade_signals:
            sig_dates = [s['date'] for s in trade_signals if s['date'] in df_chart.index]
            sig_prices = [df_chart.loc[d, 'Low'] * 0.98 for d in sig_dates]
            sig_labels = [f"▲ {s['label']}" for s in trade_signals if s['date'] in df_chart.index]

            fig.add_trace(go.Scatter(
                x=sig_dates, y=sig_prices, mode="markers+text",
                marker=dict(symbol="triangle-up", size=14, color="#00e676", line=dict(width=1.5, color="#ffffff")),
                text=sig_labels, textposition="bottom center",
                textfont=dict(color="#00e676", size=11, family="Arial Black"),
                name="Signal Entrée Impulsion"
            ), row=1, col=1)

        # Lignes Stop Loss, TP1 et TP2
        if is_impulse_strategy and active_asset and active_asset.get("impulse_sl"):
            sl_val = active_asset['impulse_sl']
            tp1_val = active_asset.get('impulse_tp1')
            tp2_val = active_asset.get('impulse_tp2')
            fig.add_hline(y=sl_val, line_dash="dash", line_color="#ff1744", annotation_text=f"SL (Bas Bear): ${sl_val}", row=1, col=1)
            if tp1_val:
                fig.add_hline(y=tp1_val, line_dash="dash", line_color="#00e676", annotation_text=f"TP1 (50% @ 1:1): ${tp1_val}", row=1, col=1)
            if tp2_val:
                fig.add_hline(y=tp2_val, line_dash="dash", line_color="#00d4ff", annotation_text=f"TP2 (35% @ 1:3): ${tp2_val}", row=1, col=1)

        # Étage 2 : RSI 21
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['rsi21'], line=dict(color='#ffd600', width=2), name='RSI 21'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff5252", annotation_text="Surachat 70 (Déclencheur)", row=2, col=1)
        fig.add_hline(y=50, line_dash="solid", line_color="#ffffff", annotation_text="Niveau 50", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00e676", annotation_text="Survente 30", row=2, col=1)

        # Étage 3 : Paolo BBW
        if active_bbw_series is not None and active_bbw_min is not None:
            fig.add_trace(go.Scatter(x=df_chart.index, y=active_bbw_series, line=dict(color='#1e90ff', width=2), name=f'Paolo BBW % ({macro_name})'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=active_bbw_min, line=dict(color='#ff1744', width=1.5, dash='dot'), name='Seuil Compression (Min)'), row=3, col=1)

        fig.update_layout(
            template="plotly_dark", height=860, margin=dict(l=40, r=40, t=65, b=40), hovermode="x unified"
        )
        
        # Abscisse de l'étage 1 (Prix)
        fig.update_xaxes(
            showticklabels=True, tickformat="%Y", dtick="M12",
            tickfont=dict(color="#00d4ff", size=13, family="Arial Black"),
            showgrid=True, gridcolor="rgba(255, 255, 255, 0.18)", gridwidth=1.5,
            tickangle=0, row=1, col=1
        )
        # Étage 2 (RSI)
        fig.update_xaxes(showticklabels=False, showgrid=True, gridcolor="rgba(255, 255, 255, 0.12)", gridwidth=1.5, dtick="M12", row=2, col=1)
        # Étage 3 (BBW)
        fig.update_xaxes(
            showticklabels=True, tickformat="%b %Y", dtick="M12",
            tickfont=dict(color="#ffffff", size=11), showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.18)", gridwidth=1.5, tickangle=-25, row=3, col=1
        )

        fig.update_yaxes(title_text="Prix ($)", row=1, col=1)
        fig.update_yaxes(title_text="RSI", range=[10, 90], row=2, col=1)
        fig.update_yaxes(title_text="BBW %", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)
