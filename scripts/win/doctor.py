#!/usr/bin/env python3
"""
Auto-diagnostic de l'installation native Windows de Power Market Intelligence
Agent.

Verifie concretement ce qui empeche un demarrage, sans Docker :
  1. Python 3.10 - 3.12 en 64 bits (numpy 1.26.4 / pydantic-core 2.16.3 n'ont
     pas de wheel pour 3.13)
  2. Fichier .env present et coherent pour un lancement local
  3. Dependances backend obligatoires importables
  4. Dependances optionnelles (LLM, LangGraph, ENTSO-E...) -> avertissement seul
  5. Dependances frontend importables
  6. `app.main` importable : c'est LA preuve que le backend demarre
  7. knowledge_base/ et backend/data_samples/ accessibles
  8. Ports backend / frontend libres
  9. frontend/.streamlit/config.toml present
 10. backend/generated/ accessible en ecriture

Codes de sortie : 0 = tout est bon, 1 = au moins une erreur bloquante.

Usage :
    python scripts/win/doctor.py --root . --backend-port 8000 --frontend-port 8501
"""
from __future__ import annotations

import argparse
import importlib
import io
import os
import socket
import struct
import sys
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

# Modules indispensables au backend (backend/requirements.txt)
BACKEND_REQUIRED = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("requests", "requests"),
    ("httpx", "httpx"),
    ("sqlalchemy", "sqlalchemy"),
    ("pptx", "python-pptx"),
    ("docx", "python-docx"),
    ("reportlab", "reportlab"),
    ("PIL", "Pillow"),
    ("openpyxl", "openpyxl"),
    ("plotly", "plotly"),
    ("structlog", "structlog"),
    ("orjson", "orjson"),
    ("aiofiles", "aiofiles"),
    ("multipart", "python-multipart"),
    ("dotenv", "python-dotenv"),
    ("tenacity", "tenacity"),
]

# Modules optionnels : absents => l'application fonctionne quand meme
BACKEND_OPTIONAL = [
    ("langgraph", "langgraph", "orchestration LangGraph (fallback routing simple sinon)"),
    ("langchain", "langchain", "chaines LangChain"),
    ("openai", "openai", "provider OpenAI"),
    ("anthropic", "anthropic", "provider Anthropic"),
    ("tiktoken", "tiktoken", "comptage de tokens"),
    ("entsoe", "entsoe-py", "connecteur ENTSO-E (inutilise sans cle)"),
    ("polars", "polars", "dataframes Polars"),
    ("scipy", "scipy", "statistiques avancees"),
    ("matplotlib", "matplotlib", "graphiques matplotlib"),
]

FRONTEND_REQUIRED = [
    ("streamlit", "streamlit"),
    ("plotly", "plotly"),
    ("pandas", "pandas"),
    ("requests", "requests"),
    ("streamlit_option_menu", "streamlit-option-menu"),
    ("streamlit_extras", "streamlit-extras"),
]

OK, WARN, FAIL = "OK", "WARN", "FAIL"


class Reporter:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self._section = ""

    def section(self, title: str) -> None:
        self._section = title
        print(f"\n  {title}")
        print("  " + "-" * (len(title) + 2))

    def add(self, status: str, label: str, detail: str = "") -> None:
        tag = {"OK": "  [ OK ]", "WARN": "  [WARN]", "FAIL": "  [FAIL]"}[status]
        line = f"{tag} {label}"
        if detail:
            line += f"  -- {detail}"
        print(line)
        if status == FAIL:
            self.errors += 1
        elif status == WARN:
            self.warnings += 1

    def ok(self, label: str, detail: str = "") -> None:
        self.add(OK, label, detail)

    def warn(self, label: str, detail: str = "") -> None:
        self.add(WARN, label, detail)

    def fail(self, label: str, detail: str = "") -> None:
        self.add(FAIL, label, detail)


def try_import(module_name: str) -> Tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as exc:  # noqa: BLE001 - on veut remonter n'importe quelle erreur
        return False, f"{type(exc).__name__}: {exc}"


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def check_python(rep: Reporter) -> None:
    rep.section("1. Interpreteur Python")
    vi = sys.version_info
    version = f"{vi.major}.{vi.minor}.{vi.micro}"
    bits = struct.calcsize("P") * 8
    rep.ok(f"Python {version} ({bits} bits)", sys.executable)
    if vi.major != 3 or not (10 <= vi.minor <= 12):
        rep.fail(
            "Version hors plage supportee (3.10 - 3.12 attendue)",
            "numpy 1.26.4 et pydantic-core 2.16.3 n'ont pas de wheel pour 3.13+",
        )
    if bits != 64:
        rep.fail("Python 32 bits detecte", "les wheels numpy/polars ne sont fournis qu'en 64 bits")
    rep.ok("Plateforme", f"{sys.platform} / {os.name}")


def check_env_file(rep: Reporter, root: Path, backend_port: int, frontend_port: int) -> None:
    rep.section("2. Configuration (.env)")
    env_path = root / ".env"
    if not env_path.exists():
        rep.fail(".env absent", "executez .\\setup.ps1 ou copiez .env.example vers .env")
        return
    rep.ok(".env present", str(env_path))

    values = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    db = values.get("DATABASE_URL", "")
    if db and ("@postgres" in db or "postgres:5432" in db):
        rep.fail(
            "DATABASE_URL pointe vers l'hote Docker 'postgres'",
            "videz la valeur : aucune base SQL n'est necessaire en natif",
        )
    elif db:
        rep.ok("DATABASE_URL definie", db)
    else:
        rep.ok("DATABASE_URL vide", "persistance fichier locale (backend/generated)")

    backend_url = values.get("BACKEND_URL", "")
    if backend_url and ("backend:" in backend_url or "@postgres" in backend_url):
        rep.fail("BACKEND_URL pointe vers un hote Docker", backend_url)
    else:
        rep.ok("BACKEND_URL", backend_url or f"(defaut http://localhost:{backend_port})")

    if values.get("MOCK_DATA_FALLBACK", "true").lower() in ("0", "false", "no"):
        rep.warn(
            "MOCK_DATA_FALLBACK desactive",
            "sans acces Internet aux APIs publiques, certaines pages seront vides",
        )
    else:
        rep.ok("MOCK_DATA_FALLBACK actif", "repli automatique sur des donnees realistes")

    llm = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY") if values.get(k)]
    if llm:
        rep.ok("Cle LLM detectee", ", ".join(llm))
    else:
        rep.ok("Aucune cle LLM", "le fallback local (templates experts) sera utilise")

    if values.get("ENTSOE_API_KEY"):
        rep.ok("Cle ENTSO-E detectee")
    else:
        rep.ok("Pas de cle ENTSO-E", "Energy-Charts + Open-Meteo + mock suffisent")


def check_dependencies(rep: Reporter) -> None:
    rep.section("3. Dependances backend obligatoires")
    missing: List[str] = []
    for module, dist in BACKEND_REQUIRED:
        imported, err = try_import(module)
        if imported:
            rep.ok(f"import {module}")
        else:
            rep.fail(f"import {module}", f"{dist} manquant ({err})")
            missing.append(dist)
    if missing:
        rep.fail(
            "Reinstallez les dependances",
            ".\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt",
        )

    rep.section("4. Dependances optionnelles")
    for module, dist, why in BACKEND_OPTIONAL:
        imported, _ = try_import(module)
        if imported:
            rep.ok(f"import {module}", why)
        else:
            rep.warn(f"import {module} indisponible", f"{why} ne sera pas utilise")


def check_frontend(rep: Reporter) -> None:
    rep.section("5. Dependances frontend")
    for module, dist in FRONTEND_REQUIRED:
        imported, err = try_import(module)
        if imported:
            rep.ok(f"import {module}")
        else:
            rep.fail(f"import {module}", f"{dist} manquant ({err})")


def check_backend_app(rep: Reporter, root: Path) -> None:
    """Importe reellement app.main : c'est la preuve que le backend demarre."""
    rep.section("6. Application backend (app.main)")
    backend_dir = root / "backend"
    if not backend_dir.is_dir():
        rep.fail("backend/ introuvable", str(backend_dir))
        return
    previous_cwd = os.getcwd()
    previous_path = list(sys.path)
    buffer = io.StringIO()
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    try:
        os.chdir(backend_dir)
        sys.path.insert(0, str(backend_dir))
        sys.stdout, sys.stderr = buffer, buffer
        app_module = importlib.import_module("app.main")
        app_obj = getattr(app_module, "app", None)
        routes = len(getattr(app_obj, "routes", [])) if app_obj is not None else 0
    except Exception:  # noqa: BLE001
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        rep.fail("import app.main a echoue")
        print("".join(traceback.format_exception(*sys.exc_info()))[:2000])
        return
    finally:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        os.chdir(previous_cwd)
        sys.path[:] = previous_path

    if routes > 0:
        rep.ok(f"import app.main reussi", f"{routes} routes FastAPI enregistrees")
    else:
        rep.fail("app.main importe mais aucune route n'est enregistree")

    generated = backend_dir / "generated"
    if generated.is_dir():
        rep.ok("backend/generated/ present", "sorties PPTX/DOCX/PDF/JSON")
    else:
        rep.warn("backend/generated/ absent", "il sera cree au premier lancement")


def check_assets(rep: Reporter, root: Path) -> None:
    rep.section("7. Ressources du projet")
    kb = root / "knowledge_base"
    if kb.is_dir():
        md = list(kb.rglob("*.md"))
        if md:
            rep.ok("knowledge_base/", f"{len(md)} fichiers markdown")
        else:
            rep.warn("knowledge_base/ vide", "la base integree de secours sera utilisee")
    else:
        rep.warn("knowledge_base/ introuvable", "la base integree de secours sera utilisee")

    samples = root / "backend" / "data_samples"
    if samples.is_dir() and any(samples.iterdir()):
        rep.ok("backend/data_samples/", ", ".join(sorted(p.name for p in samples.iterdir())))
    else:
        rep.warn("backend/data_samples/ vide", "les echantillons CSV/JSON de demo manquent")

    cfg = root / "frontend" / ".streamlit" / "config.toml"
    if cfg.is_file():
        rep.ok("frontend/.streamlit/config.toml present")
    else:
        rep.warn(
            "frontend/.streamlit/config.toml absent",
            "Streamlit utilisera ses valeurs par defaut (0.0.0.0, invite navigateur)",
        )


def check_ports(rep: Reporter, backend_port: int, frontend_port: int) -> None:
    rep.section("8. Ports")
    for label, port in (("Backend", backend_port), ("Frontend", frontend_port)):
        if port_is_free(port):
            rep.ok(f"Port {port} ({label}) libre")
        else:
            rep.warn(
                f"Port {port} ({label}) deja occupe",
                f".\\start.ps1 -{label}Port <autre_port>",
            )


def check_writable(rep: Reporter, root: Path) -> None:
    rep.section("9. Ecriture disque")
    targets = [root / "backend" / "generated", root / "logs"]
    for target in targets:
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".pmi_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            rep.ok(f"Ecriture possible", str(target))
        except Exception as exc:  # noqa: BLE001
            rep.fail(f"Ecriture impossible dans {target}", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-diagnostic de l'installation.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=8501)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print("=" * 70)
    print("  Power Market Intelligence Agent - diagnostic d'installation")
    print(f"  Depot : {root}")
    print("=" * 70)

    rep = Reporter()
    check_python(rep)
    check_env_file(rep, root, args.backend_port, args.frontend_port)
    check_dependencies(rep)
    check_frontend(rep)
    check_backend_app(rep, root)
    check_assets(rep, root)
    check_ports(rep, args.backend_port, args.frontend_port)
    check_writable(rep, root)

    print("")
    print("=" * 70)
    if rep.errors:
        print(f"  DIAGNOSTIC : {rep.errors} ERREUR(S), {rep.warnings} avertissement(s)")
        print("  -> voir les lignes [FAIL] ci-dessus, puis relancez .\\setup.ps1")
    else:
        print(f"  DIAGNOSTIC : OK ({rep.warnings} avertissement(s) non bloquant(s))")
        print("  -> vous pouvez lancer :  .\\start.ps1")
    print("=" * 70)
    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
