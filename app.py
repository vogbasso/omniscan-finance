import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

from src.providers.crypto import BinanceCryptoProvider
from src.providers.markets import UnifiedMarketProvider

st.set_page_config(
    page_title="OmniScan Finance - Grand Scan 5/20/80",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Barre Latérale
st.sidebar.title("🌐 OmniScan Finance")
st.sidebar.caption("Architecte & Auteur : **Vogel Paolo BASSO**")

lang = st.sidebar.selectbox("Langue / Language", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"
t = load_locale(lang_code)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ " + ("Configuration du Grand Scan" if lang_code == "fr" else "Master Scan Settings"))

market_options = {
    "stocks": t["menu_stocks"],
    "crypto": t["menu_crypto"],
    "forex": t["menu_forex"],
    "commodities": t["menu_commodities"],
    "indices": t["menu_indices"],
    "etf": t["menu_etf"]
}

selected_category = st.sidebar.selectbox(
    "Choisir la catégorie à scanner" if lang_code == "fr" else "Select asset category to scan",
    options=list(market_options.keys()),
    format_func=lambda x: market_options[x]
)

scan_limit = st.sidebar.slider(
    "Nombre d'actifs à scanner" if lang_code == "fr" else "Number of assets to scan",
    min_value=10, max_value=100, value=25, step=5
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 " + ("Recherche Ciblée" if lang_code == "fr" else "Targeted Search"))
custom_search = st.sidebar.text_input(
    "Ticker personnalisé (ex: PLTR, AMD, SOL/USDT)" if lang_code == "fr" else "Custom Ticker (e.g. PLTR, AMD)",
    value=""
).strip().upper()

timeframe_display = "Hebdomadaire (Weekly - 1w)" if lang_code == "fr" else "Weekly (1w)"
st.sidebar.info(f"⏱️ **Timeframe** : {timeframe_display}")

st.title("📊 " + t["app_title"])

@st.cache_data(ttl=300, show_spinner=False)
def get_scanned_data(category: str, limit: int):
    results = []
    charts = {}
    if category == "crypto":
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=limit)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe="1w", limit=150)
            if data:
                data["name"] = p['symbol'].split('/')[0]
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

# RECHERCHE CIBLÉE
if custom_search:
    st.markdown("---")
    st.markdown(f"### 🎯 Recherche Ciblée : `{custom_search}`")
    custom_data = None
    custom_df = None
    if "/" in custom_search or custom_search.endswith("USDT"):
        c_provider = BinanceCryptoProvider()
        custom_data = c_provider.analyze_ticker(custom_search, timeframe="1w")
        if custom_data:
            custom_df = custom_data.pop("df", None)
            custom_data["name"] = custom_search
    else:
        custom_data = UnifiedMarketProvider.fetch_and_analyze(custom_search, timeframe="1wk")
        if custom_data:
            custom_df = custom_data.pop("df", None)
            custom_data["name"] = custom_search

    if custom_data and custom_df is not None:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Prix Actuel", f"${custom_data['price']}")
        chg = custom_data['change_pct']
        c2.metric("Var. Hebdo", f"{'▲ +' if chg > 0 else '▼ '}{chg}%")
        c3.metric("Record ATH", f"${custom_data.get('ath_price', 'N/A')}")
        c4.metric("Distance ATH", f"{custom_data.get('dist_ath_pct', 0)}%")
        c5.metric("Capitalisation", custom_data['market_cap'])
        c6.metric("Tendance Fond", t.get(custom_data['regime'], custom_data['regime']))

        fig_c = go.Figure()
        fig_c.add_trace(go.Candlestick(
            x=custom_df.index, open=custom_df['Open'], high=custom_df['High'],
            low=custom_df['Low'], close=custom_df['Close'], name="Prix"
        ))
        fig_c.add_trace(go.Scatter(x=custom_df.index, y=custom_df['ma5'], line=dict(color='#00d4ff', width=1.5), name='MM5'))
        fig_c.add_trace(go.Scatter(x=custom_df.index, y=custom_df['ma20'], line=dict(color='#ffaa00', width=2), name='MM20'))
        fig_c.add_trace(go.Scatter(x=custom_df.index, y=custom_df['ma80'], line=dict(color='#d000ff', width=2.5), name='MM80'))
        fig_c.update_layout(title=f"Graphique Hebdomadaire (5/20/80) — {custom_search}", template="plotly_dark", height=430, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_c, use_container_width=True)

# 🎯 RADAR D'ENTRÉE EN POSITION
if results:
    opportunities = [r for r in results if r.get("is_entry_zone")]
    
    st.markdown("---")
    st.subheader("🎯 " + ("RADAR SNIPER : ACTIFS À SURVEILLER POUR ENTRER EN POSITION" if lang_code == "fr" else "SNIPER RADAR : ASSETS READY FOR ENTRY"))
    
    if opportunities:
        st.success(f"🔥 {len(opportunities)} opportunité(s) de timing détectée(s) !")
        cols = st.columns(min(len(opportunities), 4))
        for idx, opp in enumerate(opportunities[:4]):
            with cols[idx]:
                st.markdown(f"#### **{opp['name']}** ({opp['symbol']})")
                st.write(f"**Prix** : `${opp['price']}`")
                st.write(f"**Signal** : `{opp['entry_type']}`")
                st.write(f"**Distance ATH** : `{opp.get('dist_ath_pct', 0)}%`")
    else:
        st.info("ℹ️ Aucun actif en zone de pullback immédiate sur cette sélection.")

    st.markdown("---")
    bull_count = sum(1 for r in results if r["regime"] == "regime_bull")
    bear_count = sum(1 for r in results if r["regime"] == "regime_bear")
    strong_bull = sum(1 for r in results if r["state"] == "state_strong_bull")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Actifs Scannés", len(results))
    k2.metric("🟢 Régime Acheteur", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
    k3.metric("🔴 Régime Vendeur", f"{bear_count} ({round(bear_count/len(results)*100)}%)")
    k4.metric("🚀 Tendances Fortes", strong_bull)

    # TABLEAU STYLISÉ AVEC ATH ET DISTANCE ATH
    st.markdown("---")
    st.subheader("📋 " + ("Résultats Détaillés du Marché" if lang_code == "fr" else "Detailed Market Results"))
    search_f = st.text_input("🔎 Filtrer dans la liste :" if lang_code == "fr" else "Quick filter:", "").strip().upper()

    table_data = []
    for r in results:
        if search_f and search_f not in r["symbol"] and search_f not in r.get("name", "").upper():
            continue
        chg_val = r["change_pct"]
        if chg_val > 0:
            chg_str = f"▲ +{chg_val:.2f}%"
        elif chg_val < 0:
            chg_str = f"▼ {chg_val:.2f}%"
        else:
            chg_str = "  0.00%"
            
        ath_p = f"${r.get('ath_price', 'N/A')}"
        d_ath = r.get('dist_ath_pct', 0.0)
        d_ath_str = f"🔥 {d_ath:.1f}%" if d_ath >= -3.0 else f"{d_ath:.1f}%"

        statut_opp = r.get("entry_type", "") if r.get("is_entry_zone") else t.get(r["state"], r["state"])
        table_data.append({
            t["col_symbol"]: r["symbol"],
            t["col_name"]: r.get("name", r["symbol"]),
            t["col_price"]: f"${r['price']}",
            t["col_change"]: chg_str,
            t["col_ath"]: ath_p,
            t["col_dist_ath"]: d_ath_str,
            t["col_volume"]: r["volume"],
            t["col_marketcap"]: r["market_cap"],
            t["col_regime"]: t.get(r["regime"], r["regime"]),
            "Opportunité / État": statut_opp
        })

    df_display = pd.DataFrame(table_data)

    def style_change_column(val):
        if "▲" in str(val):
            return "background-color: rgba(0, 230, 118, 0.18); color: #00e676; font-weight: bold; border-radius: 4px;"
        elif "▼" in str(val):
            return "background-color: rgba(255, 82, 82, 0.18); color: #ff5252; font-weight: bold; border-radius: 4px;"
        return "color: #9e9e9e;"

    def style_regime_column(val):
        if "ACHETEUR" in str(val) or "BULLISH" in str(val):
            return "background-color: rgba(0, 230, 118, 0.12); color: #00e676; font-weight: 600;"
        elif "VENDEUR" in str(val) or "BEARISH" in str(val):
            return "background-color: rgba(255, 82, 82, 0.12); color: #ff5252; font-weight: 600;"
        return ""

    def style_dist_ath(val):
        if "🔥" in str(val):
            return "background-color: rgba(255, 171, 0, 0.2); color: #ffab00; font-weight: bold;"
        return ""

    styler = df_display.style
    try:
        styled_df = styler.map(style_change_column, subset=[t["col_change"]])\
                          .map(style_regime_column, subset=[t["col_regime"]])\
                          .map(style_dist_ath, subset=[t["col_dist_ath"]])
        st.dataframe(styled_df, use_container_width=True, height=450)
    except Exception:
        try:
            styled_df = styler.applymap(style_change_column, subset=[t["col_change"]])\
                              .applymap(style_regime_column, subset=[t["col_regime"]])\
                              .applymap(style_dist_ath, subset=[t["col_dist_ath"]])
            st.dataframe(styled_df, use_container_width=True, height=450)
        except Exception:
            st.dataframe(df_display, use_container_width=True, height=450)

    # Inspecteur graphique
    st.markdown("---")
    st.subheader("📈 " + ("Inspecteur Technique Candlestick & MM (5 / 20 / 80)" if lang_code == "fr" else "Technical Candlestick & MA (5 / 20 / 80) Inspector"))
    selected_sym = st.selectbox("Sélectionnez un actif à afficher :" if lang_code == "fr" else "Select asset to inspect:", [r["symbol"] for r in results])
    df_chart = charts_cache.get(selected_sym)

    if df_chart is not None and not df_chart.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
            low=df_chart['Low'], close=df_chart['Close'], name="Prix"
        ))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma5'], line=dict(color='#00d4ff', width=1.5), name='MM5 (Court terme)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma20'], line=dict(color='#ffaa00', width=2), name='MM20 (Moyen terme)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ma80'], line=dict(color='#d000ff', width=2.5), name='MM80 (Tendance de fond)'))
        fig.update_layout(title=f"Structure Hebdo (5 / 20 / 80) — {selected_sym}", template="plotly_dark", height=550, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
