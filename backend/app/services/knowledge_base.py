"""
Module 6: Knowledge Base
Base de connaissances sur concepts marché, hypothèses modèles, doc AFRY, FAQ
"""
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import re

from ..models.schemas import KnowledgeResult, KnowledgeResponse
from ..agent.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """
    Service de base de connaissances
    - Charge fichiers markdown locaux
    - Recherche keyword + TF-IDF simple (sans dépendance lourde)
    - Synthèse via LLM si disponible
    """

    def __init__(self, kb_path: str = "knowledge_base"):
        self.kb_path = Path(kb_path)
        # Try multiple possible locations
        possible_paths = [
            Path(kb_path),
            Path("knowledge_base"),
            Path("../knowledge_base"),
            Path("/app/knowledge_base"),
            Path("backend/knowledge_base"),
            Path(__file__).parent.parent.parent.parent / "knowledge_base"
        ]
        for p in possible_paths:
            if p.exists():
                self.kb_path = p
                break

        self.documents: List[Dict[str, Any]] = []
        self.llm = LLMProvider()
        self._load_documents()

    def _load_documents(self):
        """Charge tous les .md de la knowledge base"""
        self.documents = []
        if not self.kb_path.exists():
            logger.warning(f"Knowledge base path not found: {self.kb_path}")
            # Create minimal built-in knowledge
            self.documents = self._builtin_knowledge()
            return

        md_files = glob.glob(str(self.kb_path / "**/*.md"), recursive=True)
        logger.info(f"Loading {len(md_files)} knowledge base files from {self.kb_path}")

        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                rel_path = os.path.relpath(file_path, self.kb_path)
                category = rel_path.split(os.sep)[0] if os.sep in rel_path else "general"
                title = Path(file_path).stem.replace("_", " ").title()
                # Extract first H1 as title if exists
                h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if h1_match:
                    title = h1_match.group(1).strip()

                # Extract tags from content (simple heuristic)
                tags = []
                if "capture" in content.lower():
                    tags.append("capture_rate")
                if "afry" in content.lower():
                    tags.append("afry")
                if "aurora" in content.lower():
                    tags.append("aurora")
                if "bess" in content.lower():
                    tags.append("bess")
                if "nuclear" in content.lower() or "nucléaire" in content.lower():
                    tags.append("nuclear")

                self.documents.append({
                    "title": title,
                    "content": content,
                    "category": category,
                    "source_path": file_path,
                    "rel_path": rel_path,
                    "tags": tags
                })
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

        if not self.documents:
            self.documents = self._builtin_knowledge()

        logger.info(f"Loaded {len(self.documents)} KB documents")

    def _builtin_knowledge(self) -> List[Dict[str, Any]]:
        """Knowledge minimal si fichiers manquants"""
        return [
            {
                "title": "Capture Rate",
                "content": "# Capture Rate\n\nCapture Rate = Capture Price / Baseload Price\n\nCapture Price = sum(price * generation)/sum(generation)\n\nIndique valeur marché d'une techno renouvelable vs baseload. <1 = cannibalisation.",
                "category": "concepts",
                "source_path": "builtin",
                "rel_path": "concepts/capture_rate.md",
                "tags": ["capture_rate", "market"]
            },
            {
                "title": "AFRY BID3 Model",
                "content": "# AFRY BID3\n\nModèle fondamental marché électrique européen. Optimise dispatch hourly, prend en compte intercos, RES, demande. Utilisé pour forecasts long-terme 30+ ans.",
                "category": "models",
                "source_path": "builtin",
                "rel_path": "models/afry.md",
                "tags": ["afry", "model"]
            }
        ]

    def search(self, query: str, category: Optional[str] = None, top_k: int = 5) -> KnowledgeResponse:
        """
        Recherche dans la base de connaissances
        Simple TF-IDF + keyword matching, pas de vecteur DB pour rester léger et fonctionnel sans clé
        """
        query_lower = query.lower()
        query_tokens = set(re.findall(r'\w+', query_lower))

        scored_docs = []
        for doc in self.documents:
            if category and doc["category"] != category and category != "all":
                continue

            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()

            # Score: title match (weight 3), content match, tag match
            score = 0
            # Title
            title_tokens = set(re.findall(r'\w+', title_lower))
            title_overlap = len(query_tokens & title_tokens)
            score += title_overlap * 3

            # Content
            content_tokens = set(re.findall(r'\w+', content_lower))
            content_overlap = len(query_tokens & content_tokens)
            score += content_overlap * 1

            # Exact phrase bonus
            if query_lower in content_lower:
                score += 5
            if query_lower in title_lower:
                score += 10

            # Tag bonus
            for tag in doc["tags"]:
                if tag.lower() in query_lower or query_lower in tag.lower():
                    score += 2

            # Partial keyword
            for token in query_tokens:
                if len(token) > 3 and token in content_lower:
                    score += 0.5

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = scored_docs[:top_k]

        results = []
        for score, doc in top_docs:
            # Truncate content for display
            content_snippet = doc["content"][:1000] + ("..." if len(doc["content"]) > 1000 else "")
            results.append(KnowledgeResult(
                title=doc["title"],
                content=content_snippet,
                category=doc["category"],
                relevance_score=round(float(score), 2),
                source_path=doc["rel_path"],
                tags=doc["tags"]
            ))

        # Synthesize answer via LLM if available
        synthesized = self._synthesize_answer(query, results)

        # Related questions
        related = self._generate_related_questions(query, results)

        return KnowledgeResponse(
            query=query,
            results=results,
            synthesized_answer=synthesized,
            related_questions=related
        )

    def _synthesize_answer(self, query: str, results: List[KnowledgeResult]) -> str:
        if not results:
            return "Aucun document trouvé pour cette requête. Essayez avec des mots-clés comme 'capture rate', 'AFRY', 'BESS', 'nuclear', 'negative hours'."

        if self.llm.is_available():
            try:
                context = "\n\n".join([f"Doc: {r.title}\n{r.content[:500]}" for r in results[:3]])
                prompt = f"""
Tu es un expert marché électrique européen. Réponds à la question en utilisant le contexte fourni.

Question: {query}

Contexte:
{context}

Réponds de façon concise (5-6 lignes), technique, avec exemples chiffrés si pertinent.
Si AFRY/Aurora mentionné, explique différence.
Termine par une suggestion d'analyse complémentaire.
"""
                return self.llm.generate(prompt, max_tokens=500)
            except Exception as e:
                logger.warning(f"LLM synthesis failed: {e}")

        # Fallback template synthesis
        top = results[0]
        answer = f"**{top.title}** ({top.category}) - pertinence {top.relevance_score}\n\n"
        answer += top.content[:600] + "\n\n"
        if len(results) > 1:
            answer += f"Voir aussi: {', '.join([r.title for r in results[1:3]])}\n\n"
        answer += "💡 Suggestion: Utilisez Market Analysis Engine pour quantifier ce concept sur vos données."
        return answer

    def _generate_related_questions(self, query: str, results: List[KnowledgeResult]) -> List[str]:
        base_related = {
            "capture": ["Comment calculer capture rate solaire vs éolien?", "Quel est l'impact BESS sur capture rate?", "Pourquoi capture rate <1?"],
            "afry": ["Différence AFRY vs Aurora?", "Hypothèses AFRY BID3?", "Comment challenger scénario AFRY?"],
            "bess": ["Business case BESS 2h vs 4h?", "Revenu arbitrage BESS en FR?", "Impact BESS sur negative hours?"],
            "nuclear": ["Dispo nucléaire FR historique?", "Impact nucléaire sur prix?", "EPR et futur nucléaire FR?"],
            "negative": ["Pourquoi heures négatives augmentent?", "Comment valoriser heures négatives?", "Curtailment vs prix négatifs?"],
        }
        q_lower = query.lower()
        related = []
        for key, questions in base_related.items():
            if key in q_lower:
                related.extend(questions)
        if not related:
            related = [
                "Comment calculer capture rate?",
                "Différence AFRY vs Aurora?",
                "Opportunité BESS en France?",
                "Pourquoi prix négatifs?"
            ]
        return related[:4]

    def list_categories(self) -> List[str]:
        return list(set(doc["category"] for doc in self.documents))

    def list_documents(self) -> List[Dict[str, str]]:
        return [{"title": d["title"], "category": d["category"], "path": d["rel_path"]} for d in self.documents]
