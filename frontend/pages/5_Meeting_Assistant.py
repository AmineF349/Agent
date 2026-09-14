import streamlit as st
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient

st.set_page_config(page_title="Meeting Assistant", page_icon="🤝", layout="wide")
client = APIClient()

st.title("🤝 Meeting Assistant - Prépa Réunions + CR")
st.markdown("Prépare AFRY Review, COMEX, Trading, Strategy - génère agenda, Q&A, checklist, compte rendu")

tab1, tab2 = st.tabs(["📅 Préparer Réunion", "📝 Générer Compte Rendu"])

with tab1:
    st.subheader("Préparer Réunion")

    col1, col2 = st.columns(2)
    with col1:
        meeting_type = st.selectbox("Type réunion", ["AFRY Review", "Aurora Review", "COMEX", "Trading", "Strategy", "Modeling", "Client"], index=0)
        topic = st.text_input("Topic", "Revue scénario AFRY Central 2030 FR - capture rates & BESS")
        duration = st.number_input("Durée min", 15, 180, 60)
        participants = st.text_input("Participants (séparés par virgule)", "Analystes, Trading, Modélisation, Stratégie")
    with col2:
        context = st.text_area("Contexte", "Contexte: AFRY Central 2030 FR prévoit baseload 80€ vs Aurora 70€. Écart 12% à challenger. Focus sur hypothèses gas 38€ vs forward 32€, dispo nucléaire 75%, BESS 5GW. Besoin arbitrage COMEX pour valorisation portefeuille solaire 100MW.", height=200)

    if st.button("🚀 Préparer Réunion", type="primary"):
        with st.spinner("Préparation..."):
            try:
                # Direct
                from backend.app.services.meeting_copilot import MeetingCopilot
                from backend.app.models.schemas import MeetingRequest

                req = MeetingRequest(
                    meeting_type=meeting_type,
                    topic=topic,
                    participants=[p.strip() for p in participants.split(",")] if participants else None,
                    duration_min=duration,
                    context=context
                )
                copilot = MeetingCopilot()
                result = copilot.prepare_meeting(req)

                st.success("Préparation terminée")

                st.subheader("📋 Agenda")
                for item in result.agenda:
                    st.markdown(f"**{item['time']}** | {item['topic']} | Owner: {item['owner']}")

                st.subheader("❓ Questions Challenge")
                for q in result.key_questions:
                    st.markdown(f"- {q}")

                st.subheader("✅ Checklist Préparation")
                for c in result.preparation_checklist:
                    st.markdown(f"- {c}")

                st.subheader("⚠️ Risques à Soulever")
                for r in result.risks_to_raise:
                    st.warning(r)

                st.subheader("📊 Data à Préparer")
                for d in result.data_to_prepare:
                    st.markdown(f"- {d}")

                st.subheader("📝 Executive Summary")
                st.info(result.executive_summary)

            except Exception as e:
                st.warning(f"Direct failed {e}, trying API")
                try:
                    api_result = client.prepare_meeting(meeting_type, topic, context, duration)
                    st.json(api_result)
                except Exception as e2:
                    st.error(f"API failed: {e2}")

with tab2:
    st.subheader("Générer Compte Rendu")

    meeting_type_cr = st.selectbox("Type réunion CR", ["AFRY Review", "Aurora Review", "COMEX", "Trading"], index=0, key="cr_type")
    participants_cr = st.text_input("Participants CR", "Alice (Analyste), Bob (Trading), Charlie (Stratégie)", key="cr_part")
    raw_notes = st.text_area("Notes brutes (copiez vos notes)", """
- AFRY Central 2030 FR baseload 80€ vs Aurora 70€, écart 10€
- Hypothèse gas 38€ challengée, forward 32€, à justifier
- Décidé: lancer sensibilité gas +/-20%
- Action: Alice met à jour modèle avec gas 32€ d'ici J+3
- Question ouverte: BESS 5GW réaliste? Pipeline 1GW actuel
- Next: préparer COMEX avec 3 scénarios
- Risque: si nucléaire <70%, +10€ baseload
    """, height=300)

    if st.button("📝 Générer CR", type="primary"):
        with st.spinner("Génération CR..."):
            try:
                from backend.app.services.meeting_copilot import MeetingCopilot
                from backend.app.models.schemas import MinutesRequest

                req = MinutesRequest(
                    meeting_type=meeting_type_cr,
                    raw_notes=raw_notes,
                    participants=[p.strip() for p in participants_cr.split(",")] if participants_cr else None
                )
                copilot = MeetingCopilot()
                result = copilot.generate_minutes(req)

                st.success("CR généré")

                st.subheader("📝 Résumé")
                st.info(result.summary)

                st.subheader("✅ Décisions")
                for d in result.decisions:
                    st.markdown(f"- {d}")

                st.subheader("🎯 Actions")
                for a in result.actions:
                    st.markdown(f"- **{a.get('action')}** | Owner: {a.get('owner')} | Deadline: {a.get('deadline')}")

                st.subheader("❓ Questions Ouvertes")
                for q in result.open_questions:
                    st.markdown(f"- {q}")

                st.subheader("🚀 Next Steps")
                for ns in result.next_steps:
                    st.markdown(f"- {ns}")

                st.subheader("📄 CR Formaté")
                st.markdown(result.formatted_minutes)

            except Exception as e:
                st.warning(f"Direct failed {e}, trying API")
                try:
                    api_result = client.generate_minutes(meeting_type_cr, raw_notes)
                    st.json(api_result)
                    st.markdown(api_result.get("formatted_minutes", ""))
                except Exception as e2:
                    st.error(f"API failed: {e2}")

    st.divider()
    st.markdown("### 💡 Tips Meeting")
    st.markdown("""
    - **AFRY Review**: 90min, challenger hypothèses, comparer Aurora, préparer Q&A COMEX
    - **COMEX**: 45min, exécutif, 3 risques + 3 opportunités + 1 reco, chiffré
    - **Trading**: 30min, vue court terme, hedging, signaux marché
    - Toujours envoyer pre-read 24h avant avec agenda + questions
    - CR sous 24h, avec actions owner/deadline clairs
    - Proactif: suggérer next steps, sensibilités, follow-up
    """)
