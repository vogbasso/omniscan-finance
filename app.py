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
    page_title="OmniScan Finance - Screener RSI 21 & MM 5/20/80",
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

# SÉLECTEUR DE STRATÉGIE (RSI 21 EN OPTION PAR DÉFAUT)
strategy_choice = st.sidebar.radio(
    "Méthode d'Analyse" if lang_code == "fr" else "Analysis Strategy",
    options=[
        "🌟 RSI 21 / MM 5-20 / Pullback 50 (Défaut)",
        "📊 Triple MM 5 / 20 / 80 (Regime & BBW)"
    ],
    index=0
)
is_rsi_strategy = "RSI 21" in strategy_choice

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ " + ("Configuration du Scan" if lang_code == "fr" else "Scan Settings"))

market_options = {
    "crypto": t["menu_crypto"],
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
raw_search = st.sidebar.text_input(
    "Ticker personnalisé (ex: BTC/USDT, NVDA)" if lang_code == "fr" else "Custom Ticker",
    value=""
)
custom_search = raw_search.strip().upper()

timeframe_display = "Hebdomadaire (Weekly - 1w)" if lang_code == "fr" else "Weekly (1w)"
st.sidebar.info(f"⏱️ **Timeframe** : {timeframe_display}")

# En-tête
if is_rsi_strategy:
    st.title("🌟 OmniScan Finance — Stratégie RSI 21 / Pullback 50 & MM 5-20")
    st.caption("Polarité haussière (Survente $\le 30 ightarrow$ Surachat $\ge 70$) • Pullback sous 50 • Crossover MM 5/20 • Long Only")
else:
    st.title("📊 OmniScan Finance — Stratégie Triple MM 5 / 20 / 80")
    st.caption("Régime de fond avec mémoire d'état • Faisceau 5/20/80 • Compression Paolo BBW")

@st.cache_data(ttl=300, show_spinner=False)
def get_scanned_data(category: str, limit: int):
    results = []
    charts = {}
    if category == "crypto":
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=limit)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe="1w", limit=250, meta_info=p)
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

with st.spinner("Analyse quantitative des flux..." if lang_code == "fr" else "Running quantitative scan..."):
    results, charts_cache = get_scanned_data(selected_category, scan_limit)

# GESTION DES RADARS SELON LA STRATÉGIE ACTIVE
if results:
    st.markdown("---")
    
    if is_rsi_strategy:
        # STRATÉGIE RSI 21 : RADAR SIGNAUX FRAIS + ZONE DE PULLBACK SOUS 50
        fresh_rsi_buys = [r for r in results if r.get("rsi_state") == "STATE_FRESH_BUY"]
        pullback_setups = [r for r in results if r.get("rsi_state") == "STATE_PULLBACK_50"]

        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT FRAIS (CROISEMENT MM5 > MM20 APRÈS PULLBACK < 50)")
        if fresh_rsi_buys:
            st.success(f"🔥 ALERTE ACHAT MAJEURE : {len(fresh_rsi_buys)} signal(ux) d'achat validé(s) !")
            cols1 = st.columns(min(len(fresh_rsi_buys), 4))
            for idx, sig in enumerate(fresh_rsi_buys[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
                    st.write(f"**Type** : `{sig.get('rsi21_strat', {}).get('trade_type', 'Achat Long')}`")
                    st.write(f"**Stop Loss** : `${sig.get('rsi_sl')}`")
                    st.write(f"**Objectif TP1 (1:1)** : `${sig.get('rsi_tp1')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais déclenché cette semaine sur la stratégie RSI 21.")

        st.markdown("---")
        st.subheader("🔭 RADAR 2 : ZONE DE VEILLE (PULLBACK SOUS 50 EN COURS — ATTENTE DU CROISEMENT MM5/20)")
        if pullback_setups:
            st.warning(f"👀 {len(pullback_setups)} actif(s) en respiration saine sous 50 (À l'affût du croisement MM 5 > 20) !")
            cols2 = st.columns(min(len(pullback_setups), 4))
            for idx, pb in enumerate(pullback_setups[:4]):
                with cols2[idx]:
                    st.markdown(f"#### **{pb['name']}** ({pb['symbol']})")
                    st.write(f"**Prix Actuel** : `${pb['price']}`")
                    st.write(f"**RSI (21)** : `{pb.get('rsi')} (< 50 Confirmé)`")
                    st.write(f"**MM5** : `${round(pb.get('df_m5', pb.get('price')), 2)}` | **MM20** : `${round(pb.get('df_m20', pb.get('price')), 2)}`")
                    st.write(f"**Paolo BBW** : `{pb.get('bbw')}%`")
        else:
            st.info("ℹ️ Aucun actif actuellement en phase de pullback sous 50.")

    else:
        # STRATÉGIE 5/20/80
        fresh_signals = [r for r in results if r.get("state") == "state_new_buy"]
        imminent_setups = [r for r in results if r.get("is_near_signal")]

        st.subheader("🎯 RADAR 1 : SIGNAUX D'ACHAT FRAIS (CASSURE 5/20/80)")
        if fresh_signals:
            st.success(f"🔥 {len(fresh_signals)} signal(ux) frais détecté(s) !")
            cols1 = st.columns(min(len(fresh_signals), 4))
            for idx, sig in enumerate(fresh_signals[:4]):
                with cols1[idx]:
                    st.markdown(f"#### **{sig['name']}** ({sig['symbol']})")
                    st.write(f"**Prix** : `${sig['price']}`")
                    st.write(f"**RSI (21)** : `{sig.get('rsi')}`")
        else:
            st.info("🛡️ Aucun signal d'achat frais 5/20/80 cette semaine.")

        st.markdown("---")
        st.subheader("🔭 RADAR 2 : ZONE DE VEILLE MM80")
        if imminent_setups:
            st.warning(f"👀 {len(imminent_setups)} actif(s) en attaque directe de la MM80 !")
            cols2 = st.columns(min(len(imminent_setups), 4))
            for idx, imm in enumerate(imminent_setups[:4]):
                with cols2[idx]:
                    st.markdown(f"#### **{imm['name']}** ({imm['symbol']})")
                    st.write(f"**Prix** : `${imm['price']}`")
                    st.write(f"**Cible MM80** : `${imm.get('trigger_price')}`")
        else:
            st.info("ℹ️ Aucun actif à moins de 3.5% de sa MM80.")

    # Synthèse générale
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Actifs Scannés", len(results))
    bull_count = sum(1 for r in results if (r.get("rsi_polarity") == "POLARITY_BULL" if is_rsi_strategy else r.get("regime") == "regime_bull"))
    k2.metric("🟢 Polarité Acheteuse" if is_rsi_strategy else "🟢 Régime Acheteur", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
    k3.metric("RSI Moyen", round(sum(r.get("rsi", 50) for r in results) / len(results), 1))
    squeeze_count = sum(1 for r in results if r.get("bbw_squeeze"))
    k4.metric("⚡ Squeeze Paolo BBW", squeeze_count)

    # TABLEAU GÉNÉRAL COMPLET (AFFICHE TOUJOURS LES 3 MM 5, 20, 80)
    st.markdown("---")
    st.subheader("📋 " + ("Résultats Détaillés du Marché" if lang_code == "fr" else "Detailed Market Results"))
    search_f = st.text_input("🔎 Filtrer dans la liste :" if lang_code == "fr" else "Quick filter:", "").strip().upper()

    table_data = []
    for r in results:
        if search_f and search_f not in r["symbol"] and search_f not in r.get("name", "").upper():
            continue
        chg_val = r["change_pct"]
        chg_str = f"▲ +{chg_val:.2f}%" if chg_val > 0 else (f"▼ {chg_val:.2f}%" if chg_val < 0 else "  0.00%")
        
        rsi_val = r.get("rsi", 50.0)
        rsi_display = f"{rsi_val} | {t.get(r.get('rsi_zone', 'rsi_neutral'), '')}"

        bbw_val = r.get("bbw", 0.0)
        bbw_str = f"⚡ {bbw_val:.1f}% (Squeeze)" if r.get("bbw_squeeze") else f"{bbw_val:.1f}%"

        # Gestion des colonnes selon la stratégie
        if is_rsi_strategy:
            polarity_label = "🟢 ACHETEUSE" if r.get("rsi_polarity") == "POLARITY_BULL" else "⚪ ATTENTE"
            r_state = r.get("rsi_state", "")
            if r_state == "STATE_FRESH_BUY":
                statut_str = "🔥 SIGNAL ACHAT ACTIF"
            elif r_state == "STATE_PULLBACK_50":
                statut_str = "⏳ PULLBACK < 50"
            elif r_state == "STATE_OVERBOUGHT_IMPULSE":
                statut_str = "🚀 IMPULSION (RSI ≥ 70)"
            elif r_state == "STATE_BULLISH_TREND":
                statut_str = "↗️ FLUX ACHETEUR"
            else:
                statut_str = "⚪ ATTENTE CYCLE"

            sl_str = f"${r.get('rsi_sl')}" if r.get('rsi_sl') else "—"
            tp1_str = f"${r.get('rsi_tp1')}" if r.get('rsi_tp1') else "—"

            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "MM5": f"${r.get('df_m5', r['price']):.2f}" if 'df_m5' in r else f"${r['price']:.2f}",
                "MM20": f"${r.get('df_m20', r['price']):.2f}" if 'df_m20' in r else f"${r['price']:.2f}",
                "MM80": f"${r.get('df_m80', r['price']):.2f}" if 'df_m80' in r else f"${r['price']:.2f}",
                "RSI (21)": rsi_display,
                "Polarité": polarity_label,
                "État Stratégie": statut_str,
                "Stop Loss": sl_str,
                "TP1 (1:1)": tp1_str,
                "Paolo BBW (80)": bbw_str,
                t["col_dist_ath"]: f"{r.get('dist_ath_pct', 0.0):.1f}%"
            }
        else:
            row = {
                t["col_symbol"]: r["symbol"],
                t["col_name"]: r.get("name", r["symbol"]),
                t["col_price"]: f"${r['price']}",
                t["col_change"]: chg_str,
                "MM5": f"${r.get('df_m5', r['price']):.2f}" if 'df_m5' in r else f"${r['price']:.2f}",
                "MM20": f"${r.get('df_m20', r['price']):.2f}" if 'df_m20' in r else f"${r['price']:.2f}",
                "MM80": f"${r.get('df_m80', r['price']):.2f}" if 'df_m80' in r else f"${r['price']:.2f}",
                "RSI (21)": rsi_display,
                t["col_regime"]: t.get(r["regime"], r["regime"]),
                "État Stratégie": t.get(r["state"], r["state"]),
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

    def style_polarity(val):
        if "ACHETEUSE" in str(val) or "ACHETEUR" in str(val):
            return "background-color: rgba(0, 230, 118, 0.15); color: #00e676; font-weight: bold;"
        return "color: #9e9e9e;"

    def style_bbw(val):
        if "⚡" in str(val):
            return "background-color: rgba(30, 144, 255, 0.25); color: #1e90ff; font-weight: bold;"
        return ""

    styler = df_display.style
    try:
        col_pol = "Polarité" if is_rsi_strategy else t["col_regime"]
        styled_df = styler.map(style_change, subset=[t["col_change"]])\
                          .map(style_polarity, subset=[col_pol])\
                          .map(style_bbw, subset=["Paolo BBW (80)"])
        st.dataframe(styled_df, use_container_width=True, height=450)
    except Exception:
        st.dataframe(df_display, use_container_width=True, height=450)

    # GRAPHIQUE INTERACTIF À 3 ÉTAGES (CHANDELIERS + RSI 21 AVEC NIVEAU 50 + PAOLO BBW)
    st.markdown("---")
    st.subheader("📈 " + ("Inspecteur Technique : Chandeliers + RSI 21 (Niveau 50) + Paolo BBW" if lang_code == "fr" else "Technical Inspector"))
    selected_sym = st.selectbox("Sélectionnez un actif :" if lang_code == "fr" else "Select asset:", [r["symbol"] for r in results])
    df_chart = charts_cache.get(selected_sym)

    if df_chart is not None and not df_chart.empty:
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.55, 0.23, 0.22],
            subplot_titles=(
                f"Chandeliers & MM (5 / 20 / 80) — {selected_sym}",
                "RSI (21) • Survente ≤ 30 | Zone Centrale 50 | Surachat ≥ 70",
                "Paolo BBW % (Bandes 80) & Seuil Compression (Min Lookback)"
            )
        )

        # Étage 1 : Chandeliers et MM 5, 20, 80
        fig.add_trace(go.Candlestick(
            x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
            low=df_chart['Low'], close=df_chart['Close'], name="Prix"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma5'], line=dict(color='#00d4ff', width=1.5), name='MM5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma20'], line=dict(color='#ffaa00', width=2), name='MM20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma80'], line=dict(color='#d000ff', width=2.5), name='MM80'), row=1, col=1)

        # Étage 2 : RSI 21 avec niveau 50 central
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['rsi21'], line=dict(color='#ffd600', width=2), name='RSI 21'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff5252", annotation_text="Surachat 70", row=2, col=1)
        fig.add_hline(y=50, line_dash="solid", line_color="#ffffff", annotation_text="Pivot 50 (Pullback)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00e676", annotation_text="Survente 30", row=2, col=1)

        # Étage 3 : Paolo BBW MQL5
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['bbw'], line=dict(color='#1e90ff', width=2), name='Paolo BBW %'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['bbw_min'], line=dict(color='#ff1744', width=1.5, dash='dot'), name='Seuil Compression (Min)'), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=820, xaxis_rangeslider_visible=False, margin=dict(l=40, r=40, t=50, b=30))
        fig.update_yaxes(title_text="Prix ($)", row=1, col=1)
        fig.update_yaxes(title_text="RSI", range=[10, 90], row=2, col=1)
        fig.update_yaxes(title_text="BBW %", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)
