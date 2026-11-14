import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

from src.providers.crypto import BinanceCryptoProvider
from src.providers.markets import UnifiedMarketProvider, MARKET_CATALOG

# 1. Configuration de la page
st.set_page_config(
    page_title="OmniScan Finance - Screener 5/20/80",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Chargement i18n
def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Sidebar
st.sidebar.title("🌐 OmniScan Finance")
st.sidebar.caption("Architecte & Auteur : **Vogel Paolo BASSO**")

lang = st.sidebar.selectbox("Langue / Language", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"
t = load_locale(lang_code)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ " + ("Configuration du Grand Scan" if lang_code == "fr" else "Master Scan Settings"))

market_options = {
    "crypto": t["menu_crypto"],
    "stocks": t["menu_stocks"],
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

timeframe_display = "Hebdomadaire (Weekly - 1w)" if lang_code == "fr" else "Weekly (1w)"
st.sidebar.info(f"⏱️ **Timeframe** : {timeframe_display}")

# En-tête Principal
st.title("📊 " + t["app_title"])
st.caption(f"Stratégie quantitative Triple Moyenne Mobile (5 / 20 / 80) • Base {timeframe_display}")

# 3. Chargement et Scan des Données
with st.spinner("Analyse quantitative des flux en direct..." if lang_code == "fr" else "Scanning live market data..."):
    results = []
    charts_cache = {}

    if selected_category == "crypto":
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=15)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe="1w", limit=150)
            if data:
                data["name"] = p['symbol'].split('/')[0]
                results.append(data)
    else:
        assets = UnifiedMarketProvider.get_market_assets(selected_category)
        for item in assets:
            data = UnifiedMarketProvider.fetch_and_analyze(item["symbol"], timeframe="1wk")
            if data:
                data["name"] = item["name"]
                charts_cache[item["symbol"]] = data.pop("df", None)
                results.append(data)

# 4. Métriques KPI
if results:
    bull_count = sum(1 for r in results if r["regime"] == "regime_bull")
    bear_count = sum(1 for r in results if r["regime"] == "regime_bear")
    strong_bull = sum(1 for r in results if r["state"] == "state_strong_bull")
    slowdown = sum(1 for r in results if "slowdown" in r["state"])

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Actifs Scannés", len(results))
    kpi2.metric("🟢 Régime Acheteur", f"{bull_count} ({round(bull_count/len(results)*100)}%)")
    kpi3.metric("🔴 Régime Vendeur", f"{bear_count} ({round(bear_count/len(results)*100)}%)")
    kpi4.metric("🚀 Tendances Fortes", strong_bull)

    st.markdown("---")

    # 5. Tableau des Résultats
    table_data = []
    for r in results:
        table_data.append({
            t["col_symbol"]: r["symbol"],
            t["col_name"]: r.get("name", r["symbol"]),
            t["col_price"]: f"${r['price']}",
            t["col_regime"]: t.get(r["regime"], r["regime"]),
            t["col_state"]: t.get(r["state"], r["state"])
        })

    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True, height=450)

    # 6. Section Graphique Candlestick + MM (5, 20, 80)
    st.markdown("---")
    st.subheader("📈 " + ("Graphique Interactif & Faisceau 5 / 20 / 80" if lang_code == "fr" else "Interactive Chart & 5/20/80 Overlay"))
    
    symbols_list = [r["symbol"] for r in results]
    selected_symbol = st.selectbox(
        "Sélectionnez un actif pour afficher son graphique détaillé :" if lang_code == "fr" else "Select asset to inspect chart:",
        symbols_list
    )

    # Récupération des bougies pour le graphique
    df_chart = charts_cache.get(selected_symbol)
    if df_chart is None:
        # Si crypto ou non mis en cache, on recharge l'historique
        if selected_category == "crypto":
            import ccxt
            ex = ccxt.binance()
            ohlcv = ex.fetch_ohlcv(selected_symbol, timeframe="1w", limit=100)
            df_chart = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df_chart['Date'] = pd.to_datetime(df_chart['time'], unit='ms')
            df_chart.set_index('Date', inplace=True)
            df_chart['Close'] = df_chart['close']
            df_chart['Open'] = df_chart['open']
            df_chart['High'] = df_chart['high']
            df_chart['Low'] = df_chart['low']
        else:
            ticker = yf.Ticker(selected_symbol)
            df_chart = ticker.history(period="2y", interval="1wk")

    if df_chart is not None and not df_chart.empty:
        # Calcul des moyennes pour le graphique
        df_chart['MA5'] = df_chart['Close'].ewm(span=5, adjust=False).mean()
        df_chart['MA20'] = df_chart['Close'].ewm(span=20, adjust=False).mean()
        df_chart['MA80'] = df_chart['Close'].ewm(span=80, adjust=False).mean()

        fig = go.Figure()

        # Chandeliers japonais
        fig.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart['Open'],
            high=df_chart['High'],
            low=df_chart['Low'],
            close=df_chart['Close'],
            name="Prix"
        ))

        # Moyennes mobiles
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], line=dict(color='#00d4ff', width=1.5), name='MM5 (Court terme)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], line=dict(color='#ffaa00', width=2), name='MM20 (Moyen terme)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA80'], line=dict(color='#d000ff', width=2.5), name='MM80 (Tendance de fond)'))

        fig.update_layout(
            title=f"Structure Technique Hebdomadaire (5 / 20 / 80) — {selected_symbol}",
            yaxis_title="Prix ($)",
            xaxis_title="Date",
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=False,
            margin=dict(l=40, r=40, t=50, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Aucune donnée disponible pour cette catégorie.")
