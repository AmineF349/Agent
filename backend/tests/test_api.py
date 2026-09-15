"""
Tests d'intégration HTTP de l'API (FastAPI TestClient, aucun serveur à lancer).

Couvre les points introduits pour le fonctionnement natif Windows :
- /health répond immédiatement (sonde des APIs publiques non bloquante),
- /api/v1/presentation/generate -> /files -> /download/{name},
- protection contre la traversée de répertoires sur /download,
- chemins de travail absolus et surchargeables (GENERATED_DIR).
"""
import importlib
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """
    Client HTTP sur l'application, avec GENERATED_DIR redirigé vers un dossier
    temporaire (les modules qui capturent GENERATED_DIR à l'import sont rechargés).
    """
    generated = tmp_path_factory.mktemp("generated")
    old = os.environ.get("GENERATED_DIR")
    os.environ["GENERATED_DIR"] = str(generated)

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    main = importlib.import_module("app.main")

    with TestClient(main.app) as c:
        c.generated_dir = generated  # type: ignore[attr-defined]
        yield c

    if old is None:
        os.environ.pop("GENERATED_DIR", None)
    else:
        os.environ["GENERATED_DIR"] = old


def test_root_lists_endpoints(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["health"] == "/health"
    assert "presentation" in body["endpoints"]


def test_health_is_fast_and_non_blocking(client):
    started = time.perf_counter()
    r = client.get("/health")
    elapsed = time.perf_counter() - started
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "public_apis" in body and set(body["public_apis"]) == {"energy_charts", "open_meteo"}
    # La sonde réseau tourne en arrière-plan : la réponse ne doit pas attendre les APIs externes.
    assert elapsed < 2.0, f"/health a mis {elapsed:.2f}s (doit être non bloquant)"
    assert "presentation_generator" in body["modules"]


def test_generated_dir_env_override(client):
    from app.core import paths

    assert paths.GENERATED_DIR == Path(client.generated_dir)
    assert paths.GENERATED_DIR.is_absolute()
    assert paths.KNOWLEDGE_BASE_DIR.is_absolute()
    assert paths.ENV_FILE.is_absolute()


def test_presentation_generate_list_download(client):
    payload = {
        "presentation_type": "COMEX",
        "title": "Revue Marché Électrique FR",   # accents : noms de fichiers non-ASCII
        "subtitle": "Test",
        "slides": [{"title": "Slide 1", "bullets": ["a", "b"], "notes": "n"}],
        "author": "pytest",
        "country": "FR",
        "include_toc": True,
    }
    r = client.post("/api/v1/presentation/generate", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slide_count"] >= 1
    assert set(body["download_urls"]) == {"pptx", "docx", "pdf"}

    # Les fichiers sont écrits dans GENERATED_DIR (absolu), pas dans le répertoire courant
    for key in ("pptx_path", "docx_path", "pdf_path"):
        p = Path(body[key])
        assert p.is_absolute()
        assert p.parent == Path(client.generated_dir)
        assert p.exists()

    r = client.get("/api/v1/presentation/files")
    assert r.status_code == 200
    listing = r.json()
    assert listing["count"] >= 3
    names = {f["name"] for f in listing["files"]}
    assert Path(body["pptx_path"]).name in names

    for ext, media in (
        ("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("pdf", "application/pdf"),
    ):
        r = client.get(body["download_urls"][ext])
        assert r.status_code == 200, body["download_urls"][ext]
        assert r.headers["content-type"].startswith(media)
        assert len(r.content) > 500


@pytest.mark.parametrize(
    "name",
    [
        "inexistant.pptx",
        "../../app/main.py",
        "..%2F..%2Fapp%2Fmain.py",
        "%2e%2e%2f%2e%2e%2fapp%2fmain.py",
        "..\\..\\app\\main.py",
    ],
)
def test_download_refuses_missing_or_traversal(client, name):
    r = client.get(f"/api/v1/presentation/download/{name}")
    assert r.status_code == 404


def test_presentation_types(client):
    r = client.get("/api/v1/presentation/types")
    assert r.status_code == 200
    assert "COMEX" in r.json()


def test_knowledge_base_loaded_from_repo_root(client):
    r = client.get("/api/v1/knowledge/documents")
    if r.status_code == 404:
        pytest.skip("endpoint /documents absent")
    assert r.status_code == 200
    body = r.json()
    docs = body if isinstance(body, list) else body.get("documents", body.get("files", []))
    assert len(docs) >= 1
