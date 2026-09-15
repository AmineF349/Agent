import streamlit as st
import pandas as pd
import numpy as np
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient
from components.charts import price_timeseries_chart, price_histogram, capture_rate_gauge
import plotly.graph_objects as go

st.set_page_config(page_title="Data Analysis", page_icon="📈", layout="wide")
client = APIClient()

st.title("📈 Data Analysis - Data Quality + Market Analysis")
st.markdown("Vérifiez qualité données + calculez KPI marché (capture rate, baseload, negative hours, BESS)")

tab1, tab2, tab3 = st.tabs(["🔍 Data Quality Checker", "📊 Market Analysis Engine", "🔋 BESS Revenue"])

with tab1:
    st.subheader("Module 1: Data Quality Checker")
    st.markdown("Vérifie unités, anomalies, missing, incohérences - inspiré checks AFRY/Aurora")

    uploaded = st.file_uploader("Upload CSV ou Excel (prix, génération)", type=["csv", "xlsx"])
    data_type = st.selectbox("Type données", ["price", "capacity", "energy", "gas", "co2"], index=0)

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Utiliser sample_prices.csv"):
            sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", "data_samples", "sample_prices.csv")
            if not os.path.exists(sample_path):
                sample_path = "backend/data_samples/sample_prices.csv"
            try:
                df = pd.read_csv(sample_path)
                st.dataframe(df.head(20))
                st.session_state['dq_df'] = df
            except Exception as e:
                st.error(f"Sample not found: {e}, using mock")
                df = pd.DataFrame({"price": np.random.normal(65, 20, 100).tolist()})
                st.dataframe(df.head())
                st.session_state['dq_df'] = df

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.dataframe(df.head())
            st.session_state['dq_df'] = df
        except Exception as e:
            st.error(f"Erreur lecture: {e}")

    if 'dq_df' in st.session_state:
        df = st.session_state['dq_df']
        if st.button("Lancer Data Quality Check"):
            with st.spinner("Analyse qualité..."):
                try:
                    # Use backend via direct import for speed if API down
                    from backend.app.services.data_quality_checker import DataQualityChecker
                    checker = DataQualityChecker()
                    report = checker.check_dataframe(df, data_type=data_type)
                    st.success(f"Score qualité: {report.quality_score}/100 | Passed: {report.passed}")
                    st.markdown(f"**Summary**: {report.summary}")

                    # Missing
                    st.subheader("Valeurs manquantes")
                    st.json(report.missing_pct)

                    # Issues
                    st.subheader(f"Issues détectées: {len(report.issues)}")
                    for iss in report.issues[:20]:
                        if iss.severity == "critical":
                            st.error(f"[{iss.severity}] {iss.type} | {iss.column} | {iss.message} | Suggestion: {iss.suggestion}")
                        elif iss.severity == "high":
                            st.warning(f"[{iss.severity}] {iss.type} | {iss.column} | {iss.message}")
                        else:
                            st.info(f"[{iss.severity}] {iss.type} | {iss.column} | {iss.message}")

                    # Suggestions
                    suggestions = checker.suggest_fixes(report)
                    st.subheader("🔧 Suggestions correction")
                    for s in suggestions:
                        st.markdown(s)

                except Exception as e:
                    st.error(f"Erreur check: {e} - tentative via API")
                    try:
                        # Try API
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            df.to_csv(tmp.name, index=False)
                            result = client.data_quality_csv(tmp.name, data_type)
                            st.json(result)
                    except Exception as e2:
                        st.error(f"API aussi KO: {e2}")

with tab2:
    st.subheader("Module 2: Market Analysis Engine")
    st.markdown("Calcule Baseload, Peakload, Negative Hours, Capture Price/Rate, MVF, Cannibalisation, Volatility")

    # Input method
    input_method = st.radio("Source prix", ["Mock FR 30j", "Upload CSV", "Live API Energy-Charts", "Manuel"], index=0)

    prices = []
    generation = None
    country = st.selectbox("Pays", ["FR", "DE", "BE", "NL"], index=0, key="ma_country")
    tech = st.selectbox("Techno", ["solar", "wind_onshore", "wind_offshore"], index=0, key="ma_tech")

    if input_method == "Mock FR 30j":
        try:
            from backend.app.data.connectors.mock_generator import MockDataGenerator
        except ImportError as exc:
            MockDataGenerator = None
            st.error(
                "Générateur mock indisponible : le code backend n'est pas importable "
                f"depuis le frontend ({exc}).\n\n"
                "- **Natif Windows** : relancez `.\\setup.ps1` (backend et frontend "
                "doivent partager le même `.venv`).\n"
                "- **Docker** : le conteneur frontend ne contient pas `backend/` ; "
                "utilisez la source *Live API Energy-Charts* ou *Manuel*."
            )
        if MockDataGenerator is not None:
            gen = MockDataGenerator()
            mock_data = gen.generate_prices(country=country, days=30)
            prices = [d["price"] for d in mock_data]
            # Also generate renewable profile
            ren_data = gen.generate_renewable_profile(technology=tech, days=30, capacity_mw=100)
            generation = [d["generation_mw"] for d in ren_data]
            st.success(f"Généré {len(prices)} prix + {len(generation)} génération {tech}")

    elif input_method == "Live API Energy-Charts":
        if st.button("Fetch live FR"):
            try:
                live = client.live_prices(country=country)
                data = live.get("prices_last_week", [])
                prices = [d.get("price", 0) for d in data]
                st.success(f"Fetched {len(prices)} prix live")
            except Exception as e:
                st.error(f"Erreur fetch: {e}")

    elif input_method == "Manuel":
        prices_str = st.text_area("Prix EUR/MWh séparés par virgule", "45,42,38,52,68,78,85,82,75,68,65,62,65,72,85,92,88,75,62,52,48,44")
        try:
            prices = [float(x.strip()) for x in prices_str.split(",") if x.strip()]
        except:
            st.error("Format invalide")

    if prices:
        st.markdown(f"**{len(prices)} prix** | Min {min(prices):.1f} Max {max(prices):.1f} Mean {np.mean(prices):.1f}")

        if st.button("Calculer KPI Marché", type="primary"):
            with st.spinner("Calcul..."):
                try:
                    from backend.app.services.market_analysis_engine import MarketAnalysisEngine
                    engine = MarketAnalysisEngine()
                    result = engine.analyze(prices=prices, generation=generation, country=country, technology=tech)

                    metrics = result.metrics
                    st.success("Analyse terminée")

                    # KPI cards
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Baseload", f"{metrics.baseload} €/MWh")
                    c2.metric("Peakload", f"{metrics.peakload} €/MWh")
                    c3.metric("Offpeak", f"{metrics.offpeak} €/MWh")
                    c4.metric("Peak/Offpeak Spread", f"{metrics.peakload - metrics.offpeak:.1f} €/MWh")

                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("Negative Hours", f"{metrics.negative_hours} ({metrics.negative_hours_pct}%)")
                    c6.metric("Volatility", f"{metrics.volatility}")
                    c7.metric("P10/P50/P90", f"{metrics.p10}/{metrics.p50}/{metrics.p90}")
                    c8.metric("Min/Max", f"{metrics.min_price}/{metrics.max_price}")

                    if metrics.capture_rate:
                        st.divider()
                        st.subheader(f"🔋 KPIs {tech}")
                        cc1, cc2, cc3, cc4 = st.columns(4)
                        cc1.metric("Capture Price", f"{metrics.capture_price} €/MWh")
                        cc2.metric("Capture Rate", f"{metrics.capture_rate}", delta=f"{(metrics.capture_rate-0.8)*100:.0f}% vs 0.8")
                        cc3.metric("MVF", f"{metrics.market_value_factor}")
                        cc4.metric("Cannibalisation", f"{metrics.cannibalisation_factor}")

                        # Gauge
                        fig_gauge = capture_rate_gauge(metrics.capture_rate, tech)
                        st.plotly_chart(fig_gauge, use_container_width=True)

                    # Charts
                    st.divider()
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        fig_ts = price_timeseries_chart(prices[:168], title=f"Prix {country} - 7 jours")
                        st.plotly_chart(fig_ts, use_container_width=True)
                    with col_chart2:
                        fig_hist = price_histogram(prices, title="Distribution prix")
                        st.plotly_chart(fig_hist, use_container_width=True)

                    # Insights
                    st.subheader("💡 Insights Proactifs (Agent)")
                    for insight in result.insights:
                        st.info(insight)
                    for warn in result.warnings:
                        st.warning(warn)

                    # Chart data
                    st.json(result.chart_data)

                except Exception as e:
                    st.error(f"Erreur analysis: {e}")
                    import traceback
                    st.text(traceback.format_exc())

with tab3:
    st.subheader("🔋 BESS Revenue Estimator")
    st.markdown("Estime revenu arbitrage BESS avec perfect foresight simplifié (1 cycle/jour)")

    bess_capacity = st.slider("Capacité MW", 1, 100, 10)
    bess_duration = st.slider("Duration h", 1, 8, 2)
    bess_eff = st.slider("Efficacité", 0.7, 0.95, 0.85)

    # Use prices from previous tab if available
    if 'dq_df' in st.session_state or prices:
        if st.button("Calculer BESS Revenue"):
            try:
                from backend.app.services.market_analysis_engine import MarketAnalysisEngine
                engine = MarketAnalysisEngine()
                # Use prices from state or mock
                if not prices:
                    from backend.app.data.connectors.mock_generator import MockDataGenerator
                    gen = MockDataGenerator()
                    prices = [d["price"] for d in gen.generate_prices(days=30)]
                rev = engine.calculate_bess_revenue(prices, capacity_mw=bess_capacity, duration_h=bess_duration, efficiency=bess_eff)
                st.success(f"Revenu annuel: {rev['annual_revenue']} € | {rev['annual_per_mw']} €/MW/an")
                st.json(rev)
                st.info(f"💡 Avec {bess_capacity}MW/{bess_duration}h, spread moyen 30€, 1 cycle/jour, 85% efficacité: ~{rev['annual_per_mw']}€/MW/an. Ajouter FCR/aFRR/capacité pour stacking total 200-300k€/MW/an")
            except Exception as e:
                st.error(f"Erreur BESS: {e}")
    else:
        st.warning("D'abord générer prix dans onglet Market Analysis")
