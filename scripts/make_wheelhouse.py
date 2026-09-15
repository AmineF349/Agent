"""
Prepare un "wheelhouse" : toutes les dependances du projet (wheels precompilees)
dans un dossier, pour installer ensuite le projet SANS acces a PyPI
(poste isole, proxy trop restrictif, salle de formation...).

Sur une machine qui a acces a internet (n'importe quel OS) :

    python scripts/make_wheelhouse.py                              # pour CE Python / CET OS -> ./wheelhouse/
    python scripts/make_wheelhouse.py --platform win_amd64 --python-version 3.11
    python scripts/make_wheelhouse.py --all-platforms              # Windows + Linux + macOS, Python 3.10/3.11/3.12
    python scripts/make_wheelhouse.py --platform win_amd64 --python-version 3.11 --zip

Sur le poste cible (apres copie du dossier `wheelhouse/` a la racine du projet) :

    .\\setup.ps1 -Offline        (Windows)      |   ./setup.sh --offline      (Linux / macOS)

setup.* detecte automatiquement `./wheelhouse/` et installe avec
`pip install --no-index --find-links wheelhouse` ; le mode offline interdit en
plus tout acces reseau (echec explicite plutot que blocage sur le proxy).

Fonctionnement : constraints.txt verrouille TOUTES les dependances (directes et
indirectes) pour toutes les plateformes supportees, avec des marqueurs
d'environnement. Ce script evalue ces marqueurs pour la plateforme CIBLE (pas
celle de la machine courante), puis telecharge chaque wheel avec
`pip download --no-deps --platform ... --python-version ...`. Aucune resolution
n'est refaite : le wheelhouse contient exactement ce que setup.* installera.
Les outils de dev (pytest, black, flake8) sont toujours inclus (quelques Mo).
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:  # `packaging` est installe avec le projet (dependance de streamlit / matplotlib)
    from packaging.markers import Marker
except ImportError:  # sinon, la copie embarquee dans pip
    from pip._vendor.packaging.markers import Marker  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "constraints.txt"
DEFAULT_DEST = ROOT / "wheelhouse"
PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]

# Plateformes supportees par le projet. Pour chaque cible : les tags --platform
# passes a pip (pip complete lui-meme les tags compatibles plus anciens pour
# macOS et manylinux2014) et l'environnement PEP 508 servant a evaluer les marqueurs.
TARGETS = {
    "win_amd64": {
        "platforms": ["win_amd64"],
        "env": {"sys_platform": "win32", "os_name": "nt", "platform_system": "Windows", "platform_machine": "AMD64"},
    },
    "linux_x86_64": {
        "platforms": ["manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64", "manylinux_2_5_x86_64", "manylinux1_x86_64"],
        "env": {"sys_platform": "linux", "os_name": "posix", "platform_system": "Linux", "platform_machine": "x86_64"},
    },
    "macos_arm64": {
        "platforms": ["macosx_14_0_arm64"],
        "env": {"sys_platform": "darwin", "os_name": "posix", "platform_system": "Darwin", "platform_machine": "arm64"},
    },
    "macos_x86_64": {
        "platforms": ["macosx_14_0_x86_64"],
        "env": {"sys_platform": "darwin", "os_name": "posix", "platform_system": "Darwin", "platform_machine": "x86_64"},
    },
}

_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s;#]+)\s*(?:;\s*([^#]*?))?\s*(?:#.*)?$")


def current_target() -> str:
    machine = platform.machine().lower()
    if sys.platform == "win32":
        return "win_amd64"
    if sys.platform == "darwin":
        return "macos_arm64" if machine == "arm64" else "macos_x86_64"
    if machine in ("aarch64", "arm64"):
        raise SystemExit("Linux ARM64 n'est pas supporte (polars 0.20.22 n'a pas de wheel aarch64) : precisez --platform pour une autre cible.")
    return "linux_x86_64"


def marker_environment(target: str, python_version: str) -> dict:
    major, minor = python_version.split(".")
    env = {
        "python_version": python_version,
        "python_full_version": f"{python_version}.0",
        "implementation_name": "cpython",
        "implementation_version": f"{python_version}.0",
        "platform_python_implementation": "CPython",
        "platform_release": "",
        "platform_version": "",
        "extra": "",
    }
    env.update(TARGETS[target]["env"])
    return env


def pinned_requirements(target: str, python_version: str) -> list[str]:
    """Lignes `nom==version` de constraints.txt applicables a la cible."""
    env = marker_environment(target, python_version)
    reqs = []
    for raw in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = _LINE.match(raw)
        if not m:
            raise SystemExit(f"Ligne de constraints.txt non reconnue : {raw!r}")
        name, version, marker = m.groups()
        if marker and not Marker(marker).evaluate(env):
            continue
        reqs.append(f"{name}=={version}")
    return reqs


def download(dest: Path, target: str, python_version: str, extra_pip_args: list[str]) -> int:
    reqs = pinned_requirements(target, python_version)
    with tempfile.TemporaryDirectory() as tmp:
        req_file = Path(tmp) / f"wheelhouse-{target}-{python_version}.txt"
        req_file.write_text("\n".join(reqs + ["pip"]) + "\n", encoding="utf-8")
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--no-deps",                 # constraints.txt est deja la resolution complete
            "--only-binary", ":all:",
            "--disable-pip-version-check",
            "--python-version", python_version,
            "--implementation", "cp",
            "-d", str(dest),
            "-r", str(req_file),
        ]
        for tag in TARGETS[target]["platforms"]:
            cmd += ["--platform", tag]
        cmd += extra_pip_args
        env = dict(os.environ, PYTHONUTF8="1")
        subprocess.run(cmd, check=True, env=env)
    return len(reqs) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="dossier de destination (defaut : ./wheelhouse)")
    parser.add_argument("--platform", choices=sorted(TARGETS), help="plateforme cible (defaut : celle de ce Python)")
    parser.add_argument("--python-version", choices=PYTHON_VERSIONS, help="version de Python cible (defaut : celle de ce Python)")
    parser.add_argument("--all-platforms", action="store_true", help="toutes les plateformes x toutes les versions de Python supportees")
    parser.add_argument("--zip", action="store_true", help="produire aussi <dest>.zip (transfert par cle USB / partage reseau)")
    parser.add_argument("--clean", action="store_true", help="vider le dossier de destination avant de telecharger")
    parser.add_argument("pip_args", nargs="*", help="options pip supplementaires apres `--` (ex: -- --index-url https://nexus.local/simple)")
    args = parser.parse_args()

    if not CONSTRAINTS.exists():
        print("constraints.txt introuvable : lancez d'abord  python scripts/update_constraints.py")
        return 1

    dest = Path(args.dest).resolve()
    if args.clean and dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    here_py = f"{sys.version_info.major}.{sys.version_info.minor}"
    if args.all_platforms:
        combos = [(t, py) for t in TARGETS for py in PYTHON_VERSIONS]
    else:
        target = args.platform or current_target()
        py = args.python_version or here_py
        if py not in PYTHON_VERSIONS:
            print(f"Python {py} n'est pas supporte par le projet : precisez --python-version (3.10, 3.11 ou 3.12).")
            return 1
        combos = [(target, py)]

    for target, py in combos:
        print(f"\n== {target} / Python {py} ==")
        n = download(dest, target, py, args.pip_args)
        print(f"   {n} paquets pour cette cible")

    wheels = list(dest.glob("*.whl"))
    size_mb = sum(p.stat().st_size for p in wheels) / 1e6
    print(f"\n{len(wheels)} wheels dans {dest} ({size_mb:.0f} Mo)")

    if args.zip:
        archive = dest.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zf:  # les wheels sont deja compressees
            for p in sorted(wheels):
                zf.write(p, f"wheelhouse/{p.name}")
        print(f"Archive : {archive}  (a decompresser a la racine du projet cible)")

    print("\nSur le poste cible :  .\\setup.ps1 -Offline   ou   ./setup.sh --offline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
