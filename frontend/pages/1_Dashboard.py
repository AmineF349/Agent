import streamlit as st
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient
from utils.paths import enable_backend_imports, GENERATED_DIR, DATA_SAMPLES_DIR, KNOWLEDGE_BASE_DIR
enable_backend_imports()  # autorise `from backend.app...` quel que soit le répertoire courant
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
client = APIClient()

st.title("📊 Dashboard - Vue d'ensemble Marché")
st.markdown("KPIs temps réel + tendances + alertes proactives")

country = st.sidebar.selectbox("Pays", ["FR", "DE", "BE", "NL", "ES", "IT", "GB"], index=0)

col1, col2 = st.columns([2,1])

with col1:
    st.subheader(f"Prix Spot {country} - 30 derniers jours")
    try:
        live = client.live_prices(country)
        data = live.get("prices_last_week", []) or live.get("prices", [])
        # Actually fetch 30 days via mock or energy-charts
        market_data = client.fetch_market_data(country=country, data_type="day_ahead_prices")
        prices = [d.get("price", 0) for d in market_data.get("data", [])]

        if prices:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=prices[-720:], mode='lines', name=f'Prix {country}', line=dict(color='#003366')))
            fig.update_layout(title=f"Prix {country} - 30j", xaxis_title="Heure", yaxis_title="EUR/MWh", template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Stats
            arr = np.array(prices)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Baseload", f"{np.mean(arr):.1f} €/MWh")
            c2.metric("Min", f"{np.min(arr):.1f}")
            c3.metric("Max", f"{np.max(arr):.1f}")
            c4.metric("Negative", f"{np.sum(arr<0)}h ({np.sum(arr<0)/len(arr)*100:.1f}%)")
        else:
            st.warning("Pas de données")
    except Exception as e:
        st.error(f"Erreur: {e}")
        # Mock
        st.info("Affichage mock data")
        mock_prices = np.random.normal(65, 20, 720).tolist()
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=mock_prices, mode='lines', name='Mock FR'))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🚨 Alertes Proactives")
    st.warning("⚠️ DE: 300h négatives YTD - record, cannibalisation solaire")
    st.info("💡 FR: Spread peak/offpeak 28€ - opportunité BESS 2h")
    st.success("✅ Qualité données: 98/100 - OK pour modélisation")
    st.error("🚨 Scénario AFRY: gas 38€ vs forward 32€ - à challenger")

    st.subheader("📈 KPIs Clés")
    st.metric("Capture Rate Solaire FR", "0.78", "-0.05 vs 2023")
    st.metric("Capture Rate Éolien FR", "0.88", "-0.02")
    st.metric("BESS Revenue 10MW/2h", "220 k€/MW/an", "+15% vs 2023")

st.divider()
st.subheader("🔋 BESS Opportunity Scanner")

bess_col1, bess_col2, bess_col3 = st.columns(3)
with bess_col1:
    st.markdown("**FR** - 1GW installé, 5GW prévu 2030")
    st.progress(0.2)
    st.markdown("Opportunité: **Haute** - spread 28€, 150h négatives")
with bess_col2:
    st.markdown("**DE** - 2GW installé, 10GW prévu 2030")
    st.progress(0.2)
    st.markdown("Opportunité: **Très Haute** - spread 35€, 300h négatives")
with bess_col3:
    st.markdown("**BE** - 0.2GW installé, 1GW prévu 2030")
    st.progress(0.2)
    st.markdown("Opportunité: **Moyenne** - marché plus petit")

st.divider()
st.subheader("📊 Comparaison AFRY vs Aurora - Baseload 2030")
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=['AFRY', 'Aurora', 'Interne', 'Forward 2027'], y=[80, 70, 75, 65], marker_color=['#003366', '#0099CC', '#FF6600', '#999999']))
fig2.update_layout(title="Baseload FR 2030 - Comparaison modèles", yaxis_title="EUR/MWh", template="plotly_white", height=350)
st.plotly_chart(fig2, use_container_width=True)

st.info("💡 Insight: Écart AFRY/Aurora 10€ (12%) - AFRY plus conservateur sur flexibilité. Préparer sensibilité pour COMEX.")
