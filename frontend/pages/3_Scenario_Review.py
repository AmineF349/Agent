import streamlit as st
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient
import json

st.set_page_config(page_title="Scenario Review", page_icon="🔍", layout="wide")
client = APIClient()

st.title("🔍 Scenario Review - Challenger AFRY / Aurora / Interne")
st.markdown("Détecte hypothèses inhabituelles, écarts historiques, incohérences économiques - comme un senior analyst")

tab1, tab2, tab3 = st.tabs(["⚔️ Challenge Scénario", "📊 Benchmarks", "🆚 AFRY vs Aurora"])

with tab1:
    st.subheader("Challenge Scénario Long-Terme")

    col1, col2 = st.columns(2)
    with col1:
        scenario_name = st.text_input("Nom scénario", "AFRY Central 2030 FR")
        model_type = st.selectbox("Modèle", ["AFRY", "Aurora", "Internal", "Other"], index=0)
        country = st.selectbox("Pays", ["FR", "DE", "BE", "NL", "ES"], index=0)
        horizon = st.number_input("Horizon", 2025, 2060, 2030)
    with col2:
        st.markdown("**Hypothèses** (ajoutez lignes)")
        # Default assumptions
        default_assumptions = [
            {"name": "gas_price", "value": 38.5, "unit": "EUR/MWh", "year": 2030},
            {"name": "co2_price", "value": 120, "unit": "EUR/t", "year": 2030},
            {"name": "demand", "value": 580, "unit": "TWh", "year": 2030},
            {"name": "solar_capacity", "value": 45, "unit": "GW", "year": 2030},
            {"name": "wind_onshore_capacity", "value": 38, "unit": "GW", "year": 2030},
            {"name": "nuclear_availability", "value": 0.75, "unit": "factor", "year": 2030},
        ]

        assumptions_json = st.text_area("Hypothèses JSON", json.dumps(default_assumptions, indent=2), height=300)

        if st.button("Charger sample_scenario.json"):
            try:
                sample_path = "backend/data_samples/sample_scenario.json"
                if not os.path.exists(sample_path):
                    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", "data_samples", "sample_scenario.json")
                with open(sample_path) as f:
                    data = json.load(f)
                    st.json(data)
                    scenario_name = data.get("scenario_name", scenario_name)
                    model_type = data.get("model_type", model_type)
                    country = data.get("country", country)
                    horizon = data.get("horizon", horizon)
                    assumptions_json = json.dumps(data.get("assumptions", []), indent=2)
                    st.session_state['scenario_data'] = data
            except Exception as e:
                st.error(f"Erreur chargement sample: {e}")

    if st.button("🚀 Challenger Scénario", type="primary"):
        try:
            assumptions = json.loads(assumptions_json)
            scenario_payload = {
                "scenario_name": scenario_name,
                "model_type": model_type,
                "country": country,
                "horizon": horizon,
                "assumptions": assumptions
            }

            # Try direct import
            try:
                from backend.app.services.scenario_challenger import ScenarioChallenger
                from backend.app.models.schemas import ScenarioInput, ScenarioAssumption
                # Build
                assum_objs = [ScenarioAssumption(**a) for a in assumptions]
                scenario_input = ScenarioInput(
                    scenario_name=scenario_name,
                    model_type=model_type,
                    country=country,
                    horizon=horizon,
                    assumptions=assum_objs
                )
                challenger = ScenarioChallenger()
                result = challenger.challenge(scenario_input)

                st.success(f"Score: {result.overall_score}/100 | {result.summary}")

                # Issues
                st.subheader(f"Issues: {len(result.issues)}")
                for iss in result.issues:
                    if iss.severity == "critical":
                        st.error(f"[{iss.severity}] {iss.category} | {iss.assumption}: {iss.message} | Benchmark: {iss.benchmark} | Reco: {iss.recommendation}")
                    elif iss.severity == "warning":
                        st.warning(f"[{iss.severity}] {iss.category} | {iss.assumption}: {iss.message} | Reco: {iss.recommendation}")
                    else:
                        st.info(f"[{iss.severity}] {iss.category} | {iss.assumption}: {iss.message}")

                st.subheader("📊 Peer Comparison")
                st.json(result.peer_comparison)

                st.subheader("💼 Risques & Opportunités Business")
                for ro in result.risk_opportunities:
                    st.markdown(f"- {ro}")

            except Exception as e:
                st.warning(f"Direct import failed {e}, trying API")
                api_result = client.challenge_scenario(scenario_payload)
                st.json(api_result)

        except Exception as e:
            st.error(f"Erreur challenge: {e}")
            import traceback
            st.text(traceback.format_exc())

with tab2:
    st.subheader("📊 Benchmarks par Pays")
    bench_country = st.selectbox("Pays benchmark", ["FR", "DE"], index=0, key="bench")
    if st.button("Afficher Benchmarks"):
        try:
            from backend.app.models.domain import BENCHMARKS, AFRY_RANGES, AURORA_RANGES
            st.json({
                "benchmarks": BENCHMARKS.get(bench_country, BENCHMARKS["FR"]),
                "afry": AFRY_RANGES,
                "aurora": AURORA_RANGES
            })
        except Exception as e:
            st.error(f"Erreur: {e}")
            # Try API
            try:
                result = client.challenge_scenario  # dummy
                # Use market_data sources as proxy
                st.info("Utilisez API /api/v1/scenario/benchmarks/{country}")
            except:
                pass

    st.markdown("""
    **Ranges typiques 2030 FR:**
    - Gas: 20-60€, typique 35€
    - CO2: 60-150€, typique 90-120€
    - Demande: 500-650 TWh
    - Solaire: 30-60 GW
    - Éolien onshore: 30-55 GW
    - Nucléaire dispo: 65-85%
    - Capture rate solaire: 0.6-0.95
    - Negative hours: 50-800h
    """)

with tab3:
    st.subheader("🆚 AFRY BID3 vs Aurora - Comparatif")
    st.markdown("""
    | Critère | AFRY BID3 | Aurora |
    |---------|-----------|--------|
    | Focus | Réseau + dispatch | Valorisation RES/BESS |
    | Capture rate | Moins détaillé | Très détaillé |
    | BESS | Basique | Avancé (stacking) |
    | Prix | Souvent plus haut | Plus bas (plus flex) |
    | Écart typique baseload FR 2030 | 70-90€ | 60-80€ (10-20% écart) |
    """)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**AFRY BID3**")
        st.markdown("""
        - Optimisation dispatch hourly, unit commitment
        - EU 30+ pays, 50+ zones
        - Très détaillé réseau, interco, hydro
        - Bonne modélisation nucléaire FR
        - Utilisé par utilities (EDF, Engie, TotalEnergies)
        """)
    with c2:
        st.markdown("**Aurora**")
        st.markdown("""
        - Focus prix + capture rates
        - BESS modeling avancé (stacking)
        - Flexibilité demande détaillée
        - Scénarios policy nombreux
        - Utilisé par investisseurs RES/BESS
        """)

    st.info("💡 Tip Analyste: Utiliser AFRY pour réseau + prix baseload, Aurora pour capture rates + BESS. Faire moyenne ou range P10-P90. Écart >20% = investiguer hypothèses gas/CO2/demande/RES/BESS/interco.")

    if st.button("Voir détails AFRY vs Aurora via API"):
        try:
            import requests
            resp = requests.get(f"{client.base_url}/api/v1/scenario/afry-vs-aurora", timeout=10)
            st.json(resp.json())
        except Exception as e:
            st.error(f"Erreur API: {e}")
