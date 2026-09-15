#!/usr/bin/env python3
"""
Genere / met a jour le fichier .env pour un lancement natif Windows.

Pourquoi ce script existe
-------------------------
`.env.example` est ecrit pour `docker-compose` : il pointe `DATABASE_URL` vers
l'hote `postgres`, qui n'existe que dans le reseau Docker. En natif Windows il
faut une configuration equivalente sans service externe.

Regles appliquees (idempotentes) :
  * `.env` est cree a partir de `.env.example` s'il n'existe pas ;
  * les valeurs deja saisies par l'utilisateur sont conservees ;
  * `DATABASE_URL` est videe si elle pointe vers un hote Docker
    (`@postgres:`, `@localhost:5432`), car PostgreSQL n'est pas requis :
    aucun module du backend n'ouvre de connexion SQL ;
  * les cles propres au mode natif sont completees si absentes
    (BACKEND_HOST, BACKEND_URL, CORS_ORIGINS) ;
  * `frontend/.streamlit/config.toml` et les dossiers de sortie sont verifies.

Usage :
    python scripts/win/env_writer.py --root . --backend-port 8000 --frontend-port 8501
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Cles que le mode natif Windows doit maitriser.
DOCKER_DB_MARKERS = ("@postgres:", "@postgres/", "postgres:5432", "power_market_postgres")

STREAMLIT_CONFIG = """\
# Genere/verifie par scripts/win/env_writer.py
# Configuration Streamlit pour un lancement 100% local, sans Docker.
# NB: sous Docker, Dockerfile.frontend passe --server.address=0.0.0.0 en ligne
#     de commande, ce qui a precedence sur ce fichier.

[global]
developmentMode = false

[server]
address = "127.0.0.1"
port = __FRONTEND_PORT__
headless = true
# Le frontend appelle le backend cote SERVEUR (requests) : les regles CORS de
# Streamlit ne sont pas sollicitees, on garde les valeurs par defaut.
# enableCORS=false est incompatible avec enableXsrfProtection=true.
enableCORS = true
enableXsrfProtection = true
maxUploadSize = 200
fileWatcherType = "none"

[browser]
gatherUsageStats = false

[theme]
base = "light"
primaryColor = "#003366"
"""


def parse_env(text: str) -> Tuple[List[str], Dict[str, int]]:
    """Retourne (lignes, index_cle -> numero de ligne)."""
    lines = text.splitlines()
    index: Dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        # la derniere definition gagne, comme pour un vrai dotenv
        index[key] = i
    return lines, index


def value_of(lines: List[str], lineno: int) -> str:
    return lines[lineno].split("=", 1)[1].strip()


def set_key(lines: List[str], index: Dict[str, int], key: str, value: str) -> bool:
    """Met a jour une cle existante. Retourne True si une modification a eu lieu."""
    if key in index:
        current = value_of(lines, index[key])
        if current == value:
            return False
        lines[index[key]] = f"{key}={value}"
        return True
    lines.append(f"{key}={value}")
    index[key] = len(lines) - 1
    return True


def ensure_key(lines: List[str], index: Dict[str, int], key: str, value: str) -> bool:
    """Ajoute la cle uniquement si elle est absente (ne touche pas aux choix utilisateur)."""
    if key in index:
        return False
    lines.append(f"{key}={value}")
    index[key] = len(lines) - 1
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Genere le .env pour le mode natif Windows.")
    parser.add_argument("--root", default=".", help="Racine du depot")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=8501)
    parser.add_argument("--force", action="store_true",
                        help="Regenere .env depuis .env.example (ecrase l'existant)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    env_path = root / ".env"
    example_path = root / ".env.example"

    changes: List[str] = []

    # --- 1) .env ---------------------------------------------------------
    if args.force and env_path.exists():
        env_path.unlink()
        changes.append(".env supprime (--force)")

    if not env_path.exists():
        if not example_path.exists():
            print(f"[FAIL] Modele introuvable : {example_path}", file=sys.stderr)
            return 1
        env_path.write_bytes(example_path.read_bytes())
        changes.append(f".env cree depuis {example_path.name}")

    text = env_path.read_text(encoding="utf-8")
    lines, index = parse_env(text)

    # DATABASE_URL : aucune base n'est necessaire en natif.
    if "DATABASE_URL" in index:
        current = value_of(lines, index["DATABASE_URL"])
        if current and any(m in current for m in DOCKER_DB_MARKERS):
            lines[index["DATABASE_URL"]] = "DATABASE_URL="
            changes.append("DATABASE_URL videe (hote Docker -> persistance fichier locale)")
    else:
        ensure_key(lines, index, "DATABASE_URL", "")
        changes.append("DATABASE_URL ajoutee (vide)")

    # Ports / hotes
    if set_key(lines, index, "BACKEND_PORT", str(args.backend_port)):
        changes.append(f"BACKEND_PORT={args.backend_port}")
    if set_key(lines, index, "FRONTEND_PORT", str(args.frontend_port)):
        changes.append(f"FRONTEND_PORT={args.frontend_port}")
    if ensure_key(lines, index, "BACKEND_HOST", "127.0.0.1"):
        changes.append("BACKEND_HOST=127.0.0.1")
    if ensure_key(lines, index, "BACKEND_URL", f"http://127.0.0.1:{args.backend_port}"):
        changes.append(f"BACKEND_URL=http://127.0.0.1:{args.backend_port}")
    else:
        # Si l'URL pointe vers un hote Docker ("http://backend:8000"), la corriger.
        current = value_of(lines, index["BACKEND_URL"])
        if "backend:" in current or current.rstrip("/") != f"http://127.0.0.1:{args.backend_port}":
            if set_key(lines, index, "BACKEND_URL", f"http://127.0.0.1:{args.backend_port}"):
                changes.append(f"BACKEND_URL=http://127.0.0.1:{args.backend_port} (hote Docker remplace)")

    # CORS : le frontend Streamlit appelle le backend cote serveur (requests),
    # mais le navigateur peut aussi l'atteindre directement depuis Swagger.
    wanted_cors = ",".join([
        f"http://localhost:{args.frontend_port}",
        f"http://127.0.0.1:{args.frontend_port}",
        f"http://localhost:{args.backend_port}",
        f"http://127.0.0.1:{args.backend_port}",
    ])
    if "CORS_ORIGINS" in index:
        current = value_of(lines, index["CORS_ORIGINS"])
        merged = [o.strip() for o in current.split(",") if o.strip()]
        for o in wanted_cors.split(","):
            if o not in merged:
                merged.append(o)
        new_value = ",".join(merged)
        if new_value != current and set_key(lines, index, "CORS_ORIGINS", new_value):
            changes.append("CORS_ORIGINS completee avec 127.0.0.1")
    else:
        ensure_key(lines, index, "CORS_ORIGINS", wanted_cors)
        changes.append("CORS_ORIGINS ajoutee")

    if ensure_key(lines, index, "MOCK_DATA_FALLBACK", "true"):
        changes.append("MOCK_DATA_FALLBACK=true")

    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    # --- 2) frontend/.streamlit/config.toml ------------------------------
    streamlit_dir = root / "frontend" / ".streamlit"
    streamlit_cfg = streamlit_dir / "config.toml"
    streamlit_dir.mkdir(parents=True, exist_ok=True)
    expected = STREAMLIT_CONFIG.replace("__FRONTEND_PORT__", str(args.frontend_port))
    if not streamlit_cfg.exists():
        streamlit_cfg.write_text(expected, encoding="utf-8")
        changes.append("frontend/.streamlit/config.toml cree")
    else:
        current_cfg = streamlit_cfg.read_text(encoding="utf-8")
        if "__FRONTEND_PORT__" in current_cfg:
            streamlit_cfg.write_text(
                current_cfg.replace("__FRONTEND_PORT__", str(args.frontend_port)),
                encoding="utf-8",
            )
            changes.append("frontend/.streamlit/config.toml : port complete")

    # --- 3) Dossiers de sortie -------------------------------------------
    for rel in ("backend/generated", "backend/data_samples", "logs"):
        (root / rel).mkdir(parents=True, exist_ok=True)

    # --- Recapitulatif ----------------------------------------------------
    print("    [ OK ] .env pret : %s" % env_path)
    if changes:
        for c in changes:
            print("           - %s" % c)
    else:
        print("           - aucune modification necessaire (configuration deja correcte)")

    llm_keys = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY")
                if index.get(k) is not None and value_of(lines, index[k])]
    if llm_keys:
        print("           - LLM actif via : %s" % ", ".join(llm_keys))
    else:
        print("           - aucune cle LLM : le fallback local sera utilise (100% fonctionnel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
