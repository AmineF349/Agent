import streamlit as st
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient
import json

st.set_page_config(page_title="Presentation Builder", page_icon="📑", layout="wide")
client = APIClient()

st.title("📑 Presentation Builder - Slides Management/COMEX/AFRY")
st.markdown("Génère PPTX + DOCX + PDF - templates professionnels TotalEnergies-grade")

tab1, tab2 = st.tabs(["🎨 Générateur", "📂 Fichiers Générés"])

with tab1:
    st.subheader("Créer Présentation")

    col1, col2 = st.columns(2)
    with col1:
        pres_type = st.selectbox("Type présentation", ["Management", "COMEX", "AFRY Support", "Executive Note", "Market Update"], index=0)
        title = st.text_input("Titre", "Revue Marché Électrique FR 2030 - AFRY vs Aurora")
        subtitle = st.text_input("Sous-titre", "Analyse capture rates, BESS, risques & opportunités")
        country = st.selectbox("Pays", ["FR", "DE", "BE", "NL"], index=0)
        author = st.text_input("Auteur", "Power Market Intelligence Agent")
    with col2:
        include_toc = st.checkbox("Inclure table des matières", True)
        st.markdown("**Slides** (JSON)")
        default_slides = [
            {"title": "Executive Summary", "bullets": ["Baseload FR 2030: 70-80€ (AFRY 80€, Aurora 70€)", "Capture rate solaire 0.75 vs 0.70", "BESS 5-8GW 2030, revenu 200k€/MW/an", "Risque: gas 38€ vs forward 32€"], "notes": "Message clé: écart AFRY/Aurora 12%, préparer sensibilité COMEX"},
            {"title": "Hypothèses Clés", "bullets": ["Gas TTF 35€ 2030 (forward 32€)", "CO2 110€ 2030 (Fit-for-55)", "Demande FR 580 TWh (RTE)", "Solaire 45GW, Éolien 38GW onshore, 8GW offshore"], "notes": "Source: AFRY Central, RTE Bilan Prévisionnel"},
            {"title": "Capture Rates & Cannibalisation", "bullets": ["Solaire 0.78 2030 vs 0.85 2024: baisse avec +RES", "Éolien onshore 0.88 vs 0.92: moins cannibalisé", "Negative hours 250h vs 150h 2023", "BESS améliore capture rate +0.1-0.15"], "notes": "Opportunité BESS 2h/4h pour valoriser flexibilité"},
            {"title": "BESS Opportunity", "bullets": ["Pipeline FR 1GW 2024 -> 5GW 2030", "Revenu arbitrage 150-250k€/MW/an", "Stacking FCR + aFRR + capacité = 200-350k€/MW/an", "Impact: -30% negative hours avec 10GW BESS"], "notes": "Business case IRR 10-15% avec stacking"},
            {"title": "Risques & Opportunités", "bullets": ["Risque: gas haut 50€ = +10€ baseload", "Risque: nucléaire <70% dispo = +10-15€ baseload", "Opportunité: CO2 haut valorise RES/nucléaire", "Opportunité: PPA avec floor si capture rate bas"], "notes": "Préparer Q&A COMEX avec 3 scénarios sensibilité"},
            {"title": "Recommandations", "bullets": ["Valider hypothèses avec modélisation", "Lancer sensibilités gas +/-20%, CO2 +/-30%", "Évaluer BESS 10MW/2h pilote", "Préparer COMEX avec risques/opportunités chiffrés"], "notes": "Next steps: revue mensuelle, update forward, hedging"}
        ]
        slides_json = st.text_area("Slides JSON", json.dumps(default_slides, indent=2), height=400)

    if st.button("🚀 Générer Présentation", type="primary"):
        try:
            slides = json.loads(slides_json)
            payload = {
                "presentation_type": pres_type,
                "title": title,
                "subtitle": subtitle,
                "slides": slides,
                "author": author,
                "country": country,
                "include_toc": include_toc
            }

            # Try direct
            try:
                from backend.app.services.presentation_generator import PresentationGenerator
                from backend.app.models.schemas import PresentationRequest, SlideContent

                slide_objs = [SlideContent(**s) for s in slides]
                req = PresentationRequest(
                    presentation_type=pres_type,
                    title=title,
                    subtitle=subtitle,
                    slides=slide_objs,
                    author=author,
                    country=country,
                    include_toc=include_toc
                )
                gen = PresentationGenerator()
                result = gen.generate(req)
                st.success(f"Généré: {result.pptx_path} | {result.slide_count} slides")
                st.json(result.model_dump() if hasattr(result, 'model_dump') else result.__dict__)

                # Show download links
                st.markdown(f"**Fichiers générés dans** `backend/generated/` ou `generated/`")
                # List files
                import glob
                files = glob.glob("generated/*") + glob.glob("backend/generated/*") + glob.glob("/app/generated/*")
                for f in files[-5:]:
                    st.markdown(f"- {f}")

            except Exception as e:
                st.warning(f"Direct failed {e}, trying API")
                api_result = client.generate_presentation(pres_type, title, slides, subtitle, country)
                st.json(api_result)
                st.success("Généré via API")

        except Exception as e:
            st.error(f"Erreur génération: {e}")
            import traceback
            st.text(traceback.format_exc())

    st.divider()
    st.markdown("### 💡 Tips Présentation")
    st.markdown("""
    - **Management**: 10-15 slides, KPI + risques + reco, 30min
    - **COMEX**: 5-8 slides, exécutif, synthèse + arbitrage, 15min
    - **AFRY Support**: 20-30 slides, détaillé hypothèses + écarts, 60-90min
    - **Executive Note**: DOCX 2-3 pages
    - Toujours inclure: source, date, auteur, disclaimer
    - Proactif: suggérer next steps, sensibilités, Q&A
    """)

with tab2:
    st.subheader("📂 Fichiers Générés")
    import glob, os
    patterns = ["generated/*", "backend/generated/*", "/tmp/generated/*", "frontend/generated/*"]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if files:
        for f in sorted(files, key=os.path.getmtime, reverse=True)[:20]:
            st.markdown(f"- {f} | {os.path.getsize(f)} bytes | {os.path.getmtime(f)}")
            if st.button(f"Télécharger {os.path.basename(f)}", key=f):
                with open(f, "rb") as file:
                    st.download_button(label="Download", data=file, file_name=os.path.basename(f))
    else:
        st.info("Aucun fichier généré encore - lancez génération dans onglet Générateur")
        st.markdown("Chemins cherchés: generated/, backend/generated/")
