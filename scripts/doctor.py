"""
Diagnostic de l'installation native (Windows, Linux, macOS) :

    .venv\\Scripts\\python.exe scripts\\doctor.py       (Windows)   ou   .\\doctor.ps1
    .venv/bin/python scripts/doctor.py              (Linux/macOS) ou  ./doctor.sh

Verifie, sans rien modifier :
  1. l'interpreteur (version 3.10-3.12, 64 bits, venv du projet) ;
  2. les paquets installes par rapport a constraints.txt (manquants / versions differentes) ;
  3. la configuration (.env, ports, chemins knowledge_base / generated) ;
  4. les services : ports 8000/8501 occupes ? par qui ? /health repond ?
  5. le reseau : proxy, NO_PROXY, acces PyPI et aux APIs publiques (informatif).

Code de sortie : 0 = tout est bon, 1 = au moins un probleme bloquant.
A joindre a toute demande d'aide (copier la sortie).
"""
import json
import os
import platform
import re
import socket
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IS_WIN = sys.platform == "win32"
VENV_PY = ROOT / (".venv/Scripts/python.exe" if IS_WIN else ".venv/bin/python")

problems: list[str] = []
warnings: list[str] = []


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  [!!]   {msg}")


def fail(msg: str) -> None:
    problems.append(msg)
    print(f"  [ERR]  {msg}")


def info(msg: str) -> None:
    print(f"  [..]   {msg}")


def section(title: str) -> None:
    print(f"\n[{title}]")


# --------------------------------------------------------------------------
# 1. Interpreteur
# --------------------------------------------------------------------------
def check_python() -> None:
    section("1/5 Python")
    v = sys.version_info
    bits = struct.calcsize("P") * 8
    exe = Path(sys.executable).resolve()
    info(f"{platform.system()} {platform.release()} ({platform.machine()}) - Python {v.major}.{v.minor}.{v.micro} {bits} bits")
    info(f"Interpreteur : {exe}")
    if not (v.major == 3 and 10 <= v.minor <= 12):
        fail(f"Python {v.major}.{v.minor} n'est pas supporte (3.10 - 3.12 requis)")
    if bits != 64:
        fail("Python 32 bits : les wheels du projet sont 64 bits uniquement")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not in_venv:
        warn("Ce Python n'est pas un environnement virtuel : lancez plutot ce script avec le python du .venv")
    elif VENV_PY.exists() and exe != VENV_PY.resolve():
        warn(f"Ce n'est pas le .venv du projet ({VENV_PY})")
    else:
        ok("Environnement virtuel du projet")
    if not VENV_PY.exists():
        fail(".venv absent : lancez setup.ps1 / setup.sh")
    base = Path(getattr(sys, "base_prefix", sys.prefix))
    if not (base / ("python.exe" if IS_WIN else "bin/python3")).exists() and not list(base.glob("bin/python3*")) and not (base / "python.exe").exists():
        fail(f"Le Python de base du venv a disparu ({base}) : setup --force pour recreer le .venv")


# --------------------------------------------------------------------------
# 2. Paquets vs constraints.txt
# --------------------------------------------------------------------------
def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def check_packages() -> None:
    section("2/5 Dependances (constraints.txt)")
    constraints = ROOT / "constraints.txt"
    if not constraints.exists():
        fail("constraints.txt introuvable")
        return
    try:
        from packaging.markers import Marker
    except ImportError:
        from pip._vendor.packaging.markers import Marker  # type: ignore
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover
        fail("importlib.metadata indisponible")
        return

    wanted: dict[str, str] = {}
    for raw in constraints.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        req, _, marker = line.partition(";")
        name, _, ver = req.partition("==")
        if marker.strip() and not Marker(marker.strip()).evaluate():
            continue
        wanted[_normalize(name.strip())] = ver.strip()

    direct = set()
    for f in ("requirements.txt", "requirements-dev.txt"):
        for raw in (ROOT / f).read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                direct.add(_normalize(re.split(r"[\[=<>!~;]", line, 1)[0]))

    missing, different = [], []
    for name, ver in wanted.items():
        try:
            have = version(name)
        except PackageNotFoundError:
            missing.append(name)
            continue
        if have != ver:
            different.append(f"{name} {have} (attendu {ver})")
    dev_only = {"pytest", "black", "flake8", "pluggy", "iniconfig", "mccabe", "pycodestyle", "pyflakes", "pathspec", "mypy-extensions", "platformdirs", "tomli", "exceptiongroup"}
    missing_runtime = [m for m in missing if m not in dev_only]
    missing_dev = [m for m in missing if m in dev_only]
    if missing_runtime:
        fail(f"{len(missing_runtime)} paquet(s) manquant(s) : {', '.join(sorted(missing_runtime)[:12])}{' ...' if len(missing_runtime) > 12 else ''} -> relancez setup")
    elif missing_dev:
        info(f"Outils de dev non installes ({', '.join(sorted(missing_dev))}) : setup --dev / -Dev pour les tests")
    if different:
        warn(f"{len(different)} version(s) differente(s) de constraints.txt : {'; '.join(different[:8])}{' ...' if len(different) > 8 else ''}")
        info("(relancez setup pour realigner ; la CI valide uniquement les versions de constraints.txt)")
    if not missing_runtime and not different:
        ok(f"{len(wanted) - len(missing_dev)} paquets installes aux versions attendues ({len(direct)} dependances directes)")

    try:
        r = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            ok("pip check : aucun conflit")
        else:
            warn("pip check signale des conflits :\n" + r.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        warn(f"pip check impossible : {exc}")


# --------------------------------------------------------------------------
# 3. Configuration
# --------------------------------------------------------------------------
def read_dotenv(path: Path) -> dict:
    values = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def check_config() -> tuple[int, int]:
    section("3/5 Configuration")
    env_file = ROOT / ".env"
    dotenv = read_dotenv(env_file)
    if env_file.exists():
        ok(f".env present ({len(dotenv)} variables)")
    else:
        warn(".env absent (valeurs par defaut) : setup le cree a partir de .env.example")

    def port(key: str, default: int) -> int:
        try:
            return int(os.environ.get(key) or dotenv.get(key) or default)
        except ValueError:
            warn(f"{key} n'est pas un entier : {dotenv.get(key)!r}")
            return default

    bport, fport = port("BACKEND_PORT", 8000), port("FRONTEND_PORT", 8501)
    info(f"Ports : backend {bport}, frontend {fport}")
    backend_url = os.environ.get("BACKEND_URL") or dotenv.get("BACKEND_URL") or f"http://localhost:{bport}"
    if str(bport) not in backend_url:
        warn(f"BACKEND_URL ({backend_url}) ne correspond pas a BACKEND_PORT ({bport}) : le frontend risque de ne pas joindre le backend")
    keys = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "ENTSOE_API_KEY") if dotenv.get(k) or os.environ.get(k)]
    info("Cles API renseignees : " + (", ".join(keys) if keys else "aucune (mode fallback local, 100 % fonctionnel)"))

    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from app.core import paths  # noqa: E402

        kb = paths.KNOWLEDGE_BASE_DIR
        n_md = len(list(kb.rglob("*.md"))) if kb.exists() else 0
        (ok if n_md else fail)(f"Knowledge base : {kb} ({n_md} fichiers .md)")
        gen = paths.GENERATED_DIR
        try:
            gen.mkdir(parents=True, exist_ok=True)
            probe = gen / ".doctor_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            ok(f"Fichiers generes : {gen} (ecriture OK)")
        except OSError as exc:
            fail(f"Dossier des fichiers generes non inscriptible : {gen} ({exc})")
    except Exception as exc:  # noqa: BLE001
        fail(f"Import du backend impossible : {exc.__class__.__name__}: {exc}")

    check_wheelhouse()
    return bport, fport


def check_wheelhouse() -> None:
    """Wheelhouse local (installation hors-ligne) : versions de Python / plateformes couvertes."""
    wh = ROOT / "wheelhouse"
    wheels = sorted(p.name for p in wh.glob("*.whl")) if wh.is_dir() else []
    if not wheels:
        return
    compiled = [w for w in wheels if re.search(r"-cp3\d+-cp3\d+-", w)]
    minors = sorted({int(m.group(1)) for w in compiled for m in [re.search(r"-cp3(\d+)-cp3\d+-", w)] if m})
    platforms = []
    if any("win_amd64" in w for w in compiled):
        platforms.append("windows-x64")
    if any(re.search(r"manylinux.*x86_64", w) for w in compiled):
        platforms.append("linux-x86_64")
    if any(re.search(r"macosx.*arm64", w) and "x86_64" not in w for w in compiled):
        platforms.append("macos-arm64")
    if any(re.search(r"macosx.*x86_64", w) and "arm64" not in w for w in compiled):
        platforms.append("macos-x86_64")
    desc = f"{len(wheels)} wheels"
    if minors:
        desc += ", Python " + ", ".join(f"3.{m}" for m in minors) + ", " + (" ".join(platforms) or "plateforme inconnue")
    info(f"Wheelhouse present : {wh} ({desc})")
    if minors and sys.version_info.minor not in minors:
        warn(f"Le wheelhouse ne couvre pas le Python du venv (3.{sys.version_info.minor}) : setup --offline le refusera ;"
             f" regenerez-le avec  python scripts/make_wheelhouse.py --python-version 3.{sys.version_info.minor}")
    here = {"win32": "windows-x64", "darwin": "macos-arm64" if platform.machine().lower() == "arm64" else "macos-x86_64"}.get(
        sys.platform, "linux-x86_64" if platform.machine().lower() in ("x86_64", "amd64") else f"linux-{platform.machine().lower()}")
    if platforms and here not in platforms:
        warn(f"Le wheelhouse ne contient pas de wheels pour cette plateforme ({here}) : {', '.join(platforms)}")


# --------------------------------------------------------------------------
# 4. Services
# --------------------------------------------------------------------------
def http_get(url: str, timeout: float = 4.0):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # jamais de proxy pour localhost
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "pmia-doctor"}), timeout=timeout) as resp:
        return resp.status, resp.read()


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def listeners(port: int) -> str:
    """Description des processus en ecoute (best effort, multi-OS)."""
    try:
        if IS_WIN:
            out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=10).stdout
            pids = {line.split()[-1] for line in out.splitlines() if f":{port} " in line and "LISTENING" in line}
            descr = []
            for pid in pids:
                t = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10).stdout
                name = t.split('","')[0].strip('"\n ') if t.strip() and not t.startswith("INFO") else "?"
                descr.append(f"{name} (PID {pid})")
            return ", ".join(descr)
        import shutil

        if shutil.which("lsof"):
            out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=10).stdout
            rows = [line.split() for line in out.splitlines()[1:]]
            return ", ".join(sorted({f"{r[0]} (PID {r[1]})" for r in rows if len(r) > 1}))
        if shutil.which("ss"):  # Linux sans lsof
            out = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, timeout=10).stdout
            found = sorted(set(re.findall(r'users:\(\("([^"]+)",pid=(\d+)', out)))
            return ", ".join(f"{name} (PID {pid})" for name, pid in found)
        return ""
    except Exception:  # noqa: BLE001
        return ""


def check_services(bport: int, fport: int) -> None:
    section("4/5 Services")
    pid_file = ROOT / ("logs/pids.json" if IS_WIN else "logs/pids.env")
    if pid_file.exists():
        state = " ".join(pid_file.read_text(encoding="utf-8", errors="replace").split())
        info(f"Etat enregistre par start ({pid_file.name}) : {state[:200]}")
    # Backend
    if port_open(bport):
        try:
            status, body = http_get(f"http://127.0.0.1:{bport}/health")
            data = json.loads(body)
            ok(f"Backend : /health {status} - status={data.get('status')} llm={data.get('llm_type')} apis={data.get('public_apis')}")
        except Exception as exc:  # noqa: BLE001
            who = listeners(bport)
            fail(f"Le port {bport} est occupe mais /health ne repond pas ({exc.__class__.__name__}) : {who or 'processus inconnu'} -> stop puis start, ou autre port")
    else:
        info(f"Backend arrete (port {bport} libre) : lancez start.ps1 / start.sh")
    # Frontend
    if port_open(fport):
        try:
            status, _ = http_get(f"http://127.0.0.1:{fport}/_stcore/health")
            ok(f"Frontend : Streamlit repond ({status}) sur http://localhost:{fport}")
        except Exception as exc:  # noqa: BLE001
            who = listeners(fport)
            fail(f"Le port {fport} est occupe mais Streamlit ne repond pas ({exc.__class__.__name__}) : {who or 'processus inconnu'}")
    else:
        info(f"Frontend arrete (port {fport} libre)")
    # Logs
    for name in ("backend", "frontend"):
        log = ROOT / "logs" / f"{name}.log"
        if log.exists():
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()
            errs = [line for line in tail[-200:] if re.search(r"Traceback|Error|ERROR|Exception", line)]
            if errs:
                warn(f"logs/{name}.log : {len(errs)} ligne(s) d'erreur recentes, derniere : {errs[-1][:140]}")
            else:
                ok(f"logs/{name}.log : pas d'erreur dans les 200 dernieres lignes")


# --------------------------------------------------------------------------
# 5. Reseau
# --------------------------------------------------------------------------
def check_network() -> None:
    section("5/5 Reseau (informatif)")
    proxies = {k: os.environ[k] for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy") if os.environ.get(k)}
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    if proxies:
        info("Proxy : " + ", ".join(f"{k}={v}" for k, v in proxies.items()))
        if "127.0.0.1" not in no_proxy and "localhost" not in no_proxy:
            warn("NO_PROXY ne contient pas localhost,127.0.0.1 : les scripts start.* l'ajoutent, mais un lancement manuel peut passer par le proxy")
    else:
        info("Aucun proxy configure dans l'environnement")
    for label, url in (("PyPI (installation)", "https://pypi.org/simple/pip/"), ("Energy-Charts", "https://api.energy-charts.info/"), ("Open-Meteo", "https://api.open-meteo.com/")):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pmia-doctor"}), timeout=6) as resp:
                ok(f"{label} : joignable ({resp.status})")
        except urllib.error.HTTPError as exc:
            ok(f"{label} : joignable (HTTP {exc.code})")
        except Exception as exc:  # noqa: BLE001
            info(f"{label} : injoignable ({exc.__class__.__name__}) - " + ("installation possible hors-ligne via wheelhouse" if "PyPI" in label else "fallback mock automatique"))


def main() -> int:
    print("=" * 64)
    print("  Power Market Intelligence Agent - diagnostic")
    print("=" * 64)
    os.environ.setdefault("PYTHONUTF8", "1")
    check_python()
    check_packages()
    bport, fport = check_config()
    check_services(bport, fport)
    check_network()
    print()
    if problems:
        print(f"RESULTAT : {len(problems)} probleme(s) bloquant(s), {len(warnings)} avertissement(s)")
        for p in problems:
            print(f"  - {p.splitlines()[0]}")
        return 1
    print(f"RESULTAT : installation saine ({len(warnings)} avertissement(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
