import streamlit as st
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api_client import APIClient
from utils.paths import enable_backend_imports, GENERATED_DIR, DATA_SAMPLES_DIR, KNOWLEDGE_BASE_DIR
enable_backend_imports()  # autorise `from backend.app...` quel que soit le répertoire courant

st.set_page_config(page_title="Knowledge Center", page_icon="📚", layout="wide")
client = APIClient()

st.title("📚 Knowledge Center - Concepts Marché + Modèles + FAQ")
st.markdown("Base connaissances: capture rate, baseload, negative hours, BESS, interco, AFRY, Aurora, hypothèses")

tab1, tab2, tab3 = st.tabs(["🔍 Recherche", "📂 Documents", "❓ FAQ"])

with tab1:
    st.subheader("Recherche Knowledge Base")

    query = st.text_input("Question", "Explique capture rate solaire et opportunité BESS")
    category = st.selectbox("Catégorie", ["all", "concepts", "models", "general"], index=0)
    top_k = st.slider("Top K résultats", 1, 10, 5)

    if st.button("🔍 Rechercher", type="primary"):
        with st.spinner("Recherche..."):
            try:
                # Direct
                from backend.app.services.knowledge_base import KnowledgeBaseService
                kb = KnowledgeBaseService()
                result = kb.search(query, category=None if category=="all" else category, top_k=top_k)

                st.success(f"Trouvé {len(result.results)} docs")

                st.subheader("💡 Réponse Synthétisée")
                st.info(result.synthesized_answer)

                st.subheader(f"📄 Résultats ({len(result.results)})")
                for res in result.results:
                    with st.expander(f"{res.title} | {res.category} | Score {res.relevance_score} | {res.source_path}"):
                        st.markdown(f"**Catégorie**: {res.category} | **Tags**: {res.tags}")
                        st.markdown(res.content[:2000])
                        st.caption(f"Source: {res.source_path}")

                st.subheader("❓ Questions Liées")
                for q in result.related_questions:
                    if st.button(q, key=f"related_{q}"):
                        st.session_state['query'] = q
                        st.rerun()

            except Exception as e:
                st.warning(f"Direct failed {e}, trying API")
                try:
                    api_result = client.knowledge_search(query, category if category!="all" else None, top_k)
                    st.json(api_result)
                    st.markdown(api_result.get("synthesized_answer", ""))
                except Exception as e2:
                    st.error(f"API failed: {e2}")

    st.divider()
    st.markdown("### 💡 Exemples Requêtes")
    examples = [
        "Comment calculer capture rate?",
        "Différence AFRY vs Aurora?",
        "Opportunité BESS en France?",
        "Pourquoi heures négatives augmentent?",
        "Hypothèses AFRY BID3 2030?",
        "Impact nucléaire sur prix?",
        "Qu'est-ce que Market Value Factor?",
        "Comment challenger scénario gaz?",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i%2]:
            if st.button(ex, key=f"ex_{i}"):
                st.session_state['query_example'] = ex
                st.info(f"Requête: {ex} - cliquez Rechercher")

with tab2:
    st.subheader("📂 Documents Knowledge Base")

    if st.button("Lister Documents"):
        try:
            from backend.app.services.knowledge_base import KnowledgeBaseService
            kb = KnowledgeBaseService()
            docs = kb.list_documents()
            cats = kb.list_categories()

            st.markdown(f"**Catégories**: {cats}")
            st.markdown(f"**Total docs**: {len(docs)}")

            # Group by category
            by_cat = {}
            for d in docs:
                by_cat.setdefault(d['category'], []).append(d)

            for cat, docs_in_cat in by_cat.items():
                with st.expander(f"{cat} ({len(docs_in_cat)} docs)"):
                    for doc in docs_in_cat:
                        st.markdown(f"- **{doc['title']}** | `{doc['path']}`")

        except Exception as e:
            st.error(f"Erreur: {e}")
            try:
                api_docs = client.knowledge_search("capture rate", top_k=20)
                st.json(api_docs)
            except:
                pass

    st.divider()
    st.markdown("### 📖 Concepts Clés")
    st.markdown("""
    - **Capture Rate**: Prix capté / Baseload, indique cannibalisation
    - **Baseload**: Moyenne toutes heures
    - **Peakload**: Mon-Fri 8-20h
    - **Negative Hours**: Prix <0, cause surproduction RES
    - **BESS**: Stockage batteries, 2-4h, arbitrage + FCR
    - **Interco**: Liaisons entre pays, 4-8GW FR-DE
    - **AFRY BID3**: Modèle fondamental dispatch EU
    - **Aurora**: Modèle focus capture rates + BESS
    """)

with tab3:
    st.subheader("❓ FAQ")

    faq_path = str(KNOWLEDGE_BASE_DIR / "faq.md")

    try:
        with open(faq_path, 'r', encoding='utf-8') as f:
            faq_content = f.read()
        st.markdown(faq_content)
    except Exception as e:
        st.error(f"FAQ not found: {e}")
        st.markdown("""
        **Q: Besoin clé API?**
        R: Non, 100% fonctionnel sans clé grâce APIs publiques gratuites + fallback local.

        **Q: Quelle différence AFRY vs Aurora?**
        R: AFRY focus réseau + prix haut, Aurora focus capture rates + BESS + prix bas. Écart 10-20% typique.

        **Q: Comment calculer capture rate?**
        R: Capture Price = Σ(prix*gen)/Σ(gen), Capture Rate = Capture Price / Baseload. Utilisez Market Analysis Engine.

        **Q: Opportunité BESS?**
        R: Si capture rate <0.7 ou negative hours >5% ou spread peak/offpeak >30€, BESS 2-4h rentable.

        **Q: Comment challenger scénario?**
        R: Utilisez Scenario Challenger avec hypothèses gas/CO2/demande/RES. Compare vs benchmarks + forward + AFRY/Aurora.

        **Q: APIs gratuites?**
        R: Energy-Charts.info (prix day-ahead, sans clé), Open-Meteo (météo, sans clé), ENTSO-E (clé gratuite optionnelle).
        """)
