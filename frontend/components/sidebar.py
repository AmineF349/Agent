import os

import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.title("⚡ Power Market Intelligence")
        st.markdown("**Copilote analyste marchés électriques EU**")
        st.divider()
        st.markdown("### 🌍 Pays")
        country = st.selectbox("Pays", ["FR", "DE", "BE", "NL", "ES", "IT", "GB", "PL", "AT", "CH"], index=0)
        st.markdown("### 🔋 Techno")
        tech = st.selectbox("Technologie", ["solar", "wind_onshore", "wind_offshore", "bess", "nuclear"], index=0)
        st.divider()
        st.markdown("### 📊 Backend Status")
        # URL reelle du backend (definie par start.ps1 via la variable BACKEND_URL)
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
        st.markdown(f"Backend: {backend_url}")
        st.markdown(f"Docs: {backend_url}/docs")
        st.divider()
        st.markdown("### 💡 Tips")
        st.info("Astuce: Utilisez Data Analysis pour calculer capture rates, puis Scenario Review pour challenger AFRY/Aurora")
        st.divider()
        st.markdown("Made with ❤️ for TotalEnergies-like utility")
        return country, tech
