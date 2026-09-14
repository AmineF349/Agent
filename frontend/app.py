import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(__file__))

from utils.api_client import APIClient

# Page config
st.set_page_config(
    page_title="Power Market Intelligence Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for SaaS look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #003366;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #003366;
    }
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #0099CC;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚡ Power Market Intelligence")
    st.markdown("**Copilote analyste marchés électriques EU**")
    st.divider()
    country = st.selectbox("🌍 Pays", ["FR", "DE", "BE", "NL", "ES", "IT", "GB", "PL", "AT", "CH"], index=0)
    tech = st.selectbox("🔋 Technologie", ["solar", "wind_onshore", "wind_offshore", "bess", "nuclear"], index=0)
    st.divider()
    st.markdown("### 📊 Navigation")
    st.markdown("""
    - **Dashboard** : Vue d'ensemble marché
    - **Data Analysis** : Quality + Market Analysis
    - **Scenario Review** : Challenge AFRY/Aurora
    - **Presentation Builder** : Slides COMEX/Management
    - **Meeting Assistant** : Prépa réunions + CR
    - **Knowledge Center** : Concepts + FAQ
    """)
    st.divider()
    # Backend health
    client = APIClient()
    health = client.health()
    if health.get("status") == "ok":
        st.success(f"✅ Backend OK | LLM: {health.get('llm_type')} | Public APIs: {health.get('public_apis')}")
    else:
        st.error(f"❌ Backend KO: {health.get('error')} - Lancez `docker-compose up` ou `uvicorn backend.app.main:app`")
        st.markdown(f"Backend URL: {client.base_url}")

    st.divider()
    st.markdown("💡 **Tips Proactif**")
    st.info("1. Vérifiez qualité données\n2. Calculez capture rates\n3. Challengez scénario AFRY\n4. Préparez COMEX")

# Main
st.markdown('<div class="main-header">⚡ Power Market Intelligence Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Copilote quotidien analystes marchés électriques européens - TotalEnergies grade SaaS</div>', unsafe_allow_html=True)

# Top metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Modules", "6", "Data Quality, Market, Scenario, Meeting, Presentation, Knowledge")
with col2:
    st.metric("APIs Publiques", "2 gratuites", "Energy-Charts + Open-Meteo")
with col3:
    st.metric("Pays Couverts", "10", "FR, DE, BE, NL, ES, IT, GB...")
with col4:
    st.metric("LLM", "Fallback OK", "Fonctionne sans clé")

st.divider()

# Dashboard content
tab1, tab2, tab3 = st.tabs(["📈 Marché Live", "🤖 Agent Chat", "🚀 Quick Actions"])

with tab1:
    st.subheader(f"Marché Live {country} - Dernière Semaine (Energy-Charts.info - gratuit)")

    try:
        live = client.live_prices(country=country)
        st.markdown(f"**Source**: {live.get('source')} | **Points**: {live.get('count')} | **Dernier prix**: {live.get('latest')}")

        prices_data = live.get("prices_last_week", [])
        if prices_data:
            import pandas as pd
            df = pd.DataFrame(prices_data)
            if "price" in df.columns:
                # Plot
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=df["price"].tolist()[-168:], mode='lines', name=f'Prix {country}', line=dict(color='#003366')))
                fig.update_layout(title=f"Prix Day-Ahead {country} - Derniers 7 jours", xaxis_title="Heure", yaxis_title="EUR/MWh", template="plotly_white", height=400)
                st.plotly_chart(fig, use_container_width=True)

                # Metrics
                prices = df["price"].tolist()
                if len(prices) > 0:
                    import numpy as np
                    baseload = float(np.mean(prices))
                    min_p = float(np.min(prices))
                    max_p = float(np.max(prices))
                    neg = int(np.sum(np.array(prices) < 0))
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Baseload 7j", f"{baseload:.1f} €/MWh")
                    c2.metric("Min/Max", f"{min_p:.1f} / {max_p:.1f}")
                    c3.metric("Negative Hours", f"{neg}")
                    c4.metric("Volatilité", f"{np.std(prices)/baseload:.2f}" if baseload else "N/A")
        else:
            st.warning("Pas de données live, backend peut-être down ou API Energy-Charts indisponible - fallback mock utilisé")
    except Exception as e:
        st.error(f"Erreur live data: {e}")
        st.info("Lancez backend: `cd backend && uvicorn app.main:app --reload --port 8000`")

with tab2:
    st.subheader("🤖 Agent Conversationnel (LangGraph + Fallback)")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Bonjour! Je suis Power Market Intelligence Agent. Posez-moi une question sur marché électrique EU, capture rate, AFRY, BESS, etc."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ex: Analyse capture rate solaire FR, Challenge scénario AFRY 2030, Prépare réunion COMEX..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse en cours..."):
                try:
                    result = client.agent_chat(query=prompt, country=country)
                    # Show synthesis
                    synthesis = result.get("results", {}).get("synthesis", "Pas de synthèse")
                    st.markdown(synthesis)

                    # Show proactive suggestions
                    suggestions = result.get("proactive_suggestions", [])
                    if suggestions:
                        st.markdown("**💡 Suggestions proactives:**")
                        for s in suggestions:
                            st.markdown(f"- {s}")

                    # Show intent and mode
                    st.caption(f"Intent: {result.get('intent')} | Mode: {result.get('mode')} | Backend: {client.base_url}")

                    st.session_state.messages.append({"role": "assistant", "content": synthesis})
                except Exception as e:
                    err_msg = f"Erreur agent: {e} - Vérifiez backend"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})

with tab3:
    st.subheader("🚀 Quick Actions - Workflow Analyste")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1️⃣ Data Quality")
        st.markdown("Vérifiez vos fichiers CSV prix/génération")
        if st.button("Aller à Data Analysis", key="qa1"):
            st.switch_page("pages/2_Data_Analysis.py")
        st.markdown("""
        - Upload CSV
        - Détecte missing, anomalies
        - Score qualité /100
        """)

    with col2:
        st.markdown("### 2️⃣ Market Analysis")
        st.markdown("Calculez KPI marché")
        if st.button("Aller à Data Analysis", key="qa2"):
            st.switch_page("pages/2_Data_Analysis.py")
        st.markdown("""
        - Baseload, Peakload
        - Capture Rate/Price
        - Negative Hours
        - BESS revenue
        """)

    with col3:
        st.markdown("### 3️⃣ Scenario Review")
        st.markdown("Challengez AFRY/Aurora")
        if st.button("Aller à Scenario Review", key="qa3"):
            st.switch_page("pages/3_Scenario_Review.py")
        st.markdown("""
        - Hypothèses gaz/CO2
        - Écarts historiques
        - Incohérences éco
        - Risques & opportunités
        """)

    st.divider()
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("### 4️⃣ Presentation Builder")
        if st.button("Aller à Presentation Builder", key="qa4"):
            st.switch_page("pages/4_Presentation_Builder.py")
        st.markdown("Génère PPTX/COMEX/AFRY + DOCX + PDF")
    with col5:
        st.markdown("### 5️⃣ Meeting Assistant")
        if st.button("Aller à Meeting Assistant", key="qa5"):
            st.switch_page("pages/5_Meeting_Assistant.py")
        st.markdown("Agenda, Q&A, checklist, CR")
    with col6:
        st.markdown("### 6️⃣ Knowledge Center")
        if st.button("Aller à Knowledge Center", key="qa6"):
            st.switch_page("pages/6_Knowledge_Center.py")
        st.markdown("Concepts marché, AFRY, BESS, FAQ")

st.divider()
st.markdown("### 📚 Architecture Produit")
st.markdown("""
**Stack**: FastAPI + Streamlit + LangGraph + Pandas/Polars + Plotly + Docker

**APIs Publiques Gratuites (sans clé)**:
- Energy-Charts.info (Fraunhofer ISE) - prix day-ahead EU
- Open-Meteo - météo, vent, solaire

**Optionnel**:
- ENTSO-E Transparency (clé gratuite)
- OpenAI/Claude/Azure OpenAI (LLM enrichi)

**Mode Fallback**: 100% fonctionnel sans aucune clé - templates experts intégrés
""")

st.markdown("---")
st.markdown("**Power Market Intelligence Agent v1.0.0** | TotalEnergies-grade SaaS | Made for analysts, traders, stratégie, modélisation, COMEX")
