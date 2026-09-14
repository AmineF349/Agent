from fastapi import APIRouter
from typing import Optional
import logging

from ...services.knowledge_base import KnowledgeBaseService
from ...models.schemas import KnowledgeQuery, KnowledgeResponse

router = APIRouter()
kb_service = KnowledgeBaseService()
logger = logging.getLogger(__name__)

@router.post("/search", response_model=KnowledgeResponse)
async def search_knowledge(query: KnowledgeQuery):
    """
    Recherche dans base de connaissances:
    - Concepts marché (capture rate, baseload, BESS...)
    - Modèles (AFRY BID3, Aurora)
    - Hypothèses, FAQ
    """
    logger.info(f"Knowledge search: {query.query} category={query.category}")
    result = kb_service.search(query.query, category=query.category, top_k=query.top_k)
    return result

@router.get("/categories")
async def list_categories():
    return {"categories": kb_service.list_categories()}

@router.get("/documents")
async def list_documents():
    return {"documents": kb_service.list_documents(), "count": len(kb_service.documents)}

@router.get("/concept/{concept_name}")
async def get_concept(concept_name: str):
    # Quick lookup for common concepts
    result = kb_service.search(concept_name, top_k=1)
    if result.results:
        return result.results[0]
    return {"error": "Concept not found", "suggestion": "Try search endpoint"}
