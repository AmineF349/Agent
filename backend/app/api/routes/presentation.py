from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging
from pathlib import Path

from ...services.presentation_generator import PresentationGenerator
from ...models.schemas import PresentationRequest, PresentationResponse
from ...core.paths import GENERATED_DIR

router = APIRouter()
generator = PresentationGenerator()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}


def _resolve_generated_file(filename: str) -> Path:
    """Résout un nom de fichier dans GENERATED_DIR en refusant toute sortie du dossier."""
    base = GENERATED_DIR.resolve()
    candidate = (base / Path(filename).name).resolve()
    if candidate.parent != base or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


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


@router.get("/files")
async def list_generated_files(limit: int = 50):
    """Liste les fichiers générés (les plus récents en premier)."""
    files = sorted(
        (p for p in GENERATED_DIR.glob("*") if p.is_file() and p.suffix in MEDIA_TYPES),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    return {
        "directory": str(GENERATED_DIR),
        "count": len(files),
        "files": [
            {
                "name": p.name,
                "size_bytes": p.stat().st_size,
                "modified": p.stat().st_mtime,
                "download_url": f"/api/v1/presentation/download/{p.name}",
            }
            for p in files
        ],
    }


@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = _resolve_generated_file(filename)
    media_type = MEDIA_TYPES.get(file_path.suffix, "application/octet-stream")
    return FileResponse(path=file_path, filename=file_path.name, media_type=media_type)


@router.get("/types")
async def presentation_types():
    return {
        "Management": "Slides pour management énergie, focus KPI + risques",
        "COMEX": "Slides exécutives, synthèse + recommandation arbitrage",
        "AFRY Support": "Support détaillé revue AFRY, hypothèses + écarts",
        "Executive Note": "Note Word/PDF 2-3 pages",
        "Market Update": "Update marché mensuel, prix + news"
    }
