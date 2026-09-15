"""
Regenere constraints.txt : le verrou des dependances transitives du projet.

    python scripts/update_constraints.py            # met a jour constraints.txt
    python scripts/update_constraints.py --upgrade  # remonte aussi les transitives au plus recent
    python scripts/update_constraints.py --check    # verifie que constraints.txt est a jour (code 1 sinon)

requirements.txt / requirements-dev.txt restent la source de verite (pins directs) ;
constraints.txt fige en plus TOUTES les dependances indirectes, pour toutes les
plateformes supportees (Windows, Linux, macOS) et Python 3.10 a 3.12, en une seule
resolution "universelle" (marqueurs d'environnement). setup.ps1 / setup.sh et la CI
installent avec `pip install -r requirements.txt -c constraints.txt` : le meme
environnement partout, sans image Docker.

Necessite uv (https://docs.astral.sh/uv/) : installe automatiquement dans le venv
courant si absent (`pip install uv`).
"""
import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = [ROOT / "requirements.txt", ROOT / "requirements-dev.txt"]
CONSTRAINTS = ROOT / "constraints.txt"
PYTHON_MIN = "3.10"

HEADER = """\
# =============================================================================
# constraints.txt - verrou des dependances transitives (toutes plateformes)
# =============================================================================
# GENERE par scripts/update_constraints.py : ne pas editer a la main.
# Source de verite des pins directs : requirements.txt / requirements-dev.txt.
#
# Utilisation (faite automatiquement par setup.ps1, setup.sh et la CI) :
#     pip install --only-binary :all: -r requirements.txt -c constraints.txt
#
# Resolution universelle (uv pip compile --universal) valable pour Python 3.10,
# 3.11 et 3.12 sous Windows, Linux et macOS : les lignes portant un marqueur
# d'environnement ne s'appliquent qu'aux plateformes concernees.
# Toutes les versions listees existent en wheel precompilee (cp310-cp312,
# win_amd64 / manylinux x86_64 / macOS x86_64 + arm64).
# =============================================================================
"""


def uv_command() -> list[str]:
    exe = shutil.which("uv")
    if exe:
        return [exe]
    try:
        subprocess.run([sys.executable, "-m", "uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("uv absent : installation dans l'environnement courant (pip install uv)")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--only-binary", ":all:", "uv"], check=True)
    return [sys.executable, "-m", "uv"]


def compile_constraints(output: Path, upgrade: bool) -> None:
    cmd = uv_command() + [
        "pip", "compile",
        "--universal",
        "--python-version", PYTHON_MIN,
        "--only-binary", ":all:",
        "--no-header",
        "--annotation-style", "line",
        "--quiet",
        *[str(r) for r in REQUIREMENTS],
        "-o", str(output),
    ]
    if upgrade:
        cmd.append("--upgrade")
    env = dict(os.environ, UV_NO_PROGRESS="1")
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)
    body = output.read_text(encoding="utf-8")
    output.write_text(HEADER + body, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--upgrade", action="store_true", help="remonte les dependances transitives au plus recent")
    parser.add_argument("--check", action="store_true", help="verifie sans modifier ; code 1 si constraints.txt n'est pas a jour")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "constraints.txt"
        if CONSTRAINTS.exists():
            # Le fichier existant sert de preference : seules les dependances dont
            # les contraintes ont change bougent (comportement pip-tools).
            shutil.copy(CONSTRAINTS, target)
        compile_constraints(target, upgrade=args.upgrade)
        if args.check:
            if CONSTRAINTS.exists() and filecmp.cmp(target, CONSTRAINTS, shallow=False):
                print("constraints.txt est a jour.")
                return 0
            print("constraints.txt n'est PAS a jour : lancez  python scripts/update_constraints.py")
            return 1
        shutil.copy(target, CONSTRAINTS)
    n = sum(1 for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
    print(f"constraints.txt regenere : {n} dependances verrouillees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
