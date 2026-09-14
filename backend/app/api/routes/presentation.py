from fastapi import APIRouter
from fastapi.responses import FileResponse
import logging
from pathlib import Path

from ...services.presentation_generator import PresentationGenerator
from ...models.schemas import PresentationRequest, PresentationResponse

router = APIRouter()
generator = PresentationGenerator()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=PresentationResponse)
async def generate_presentation(request: PresentationRequest):
    """
    Génère présentation:
    - PPTX (slides management/COMEX/AFRY)
    - DOCX (note exécutive)
    - PDF (export)
    """
    logger.info(f"Generating presentation: {request.title} {request.presentation_type} {len(request.slides)} slides")
    result = generator.generate(request)
    return result

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path("generated") / filename
    if not file_path.exists():
        # Try absolute
        file_path = Path("/app/generated") / filename
    if not file_path.exists():
        return {"error": "File not found"}

    # Determine media type
    if filename.endswith(".pptx"):
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=file_path, filename=filename, media_type=media_type)

@router.get("/types")
async def presentation_types():
    return {
        "Management": "Slides pour management énergie, focus KPI + risques",
        "COMEX": "Slides exécutives, synthèse + recommandation arbitrage",
        "AFRY Support": "Support détaillé revue AFRY, hypothèses + écarts",
        "Executive Note": "Note Word/PDF 2-3 pages",
        "Market Update": "Update marché mensuel, prix + news"
    }
