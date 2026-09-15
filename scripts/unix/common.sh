#!/usr/bin/env bash
# Fonctions partagees par setup.sh / start.sh / stop.sh / test.sh
# (source : `. scripts/unix/common.sh`). Compatible bash 3.2+ (macOS) et Linux.
#
# Equivalent de scripts/windows/common.ps1 pour Linux / macOS.

PYTHON_MIN_MINOR=10   # 3.10
PYTHON_MAX_MINOR=12   # 3.12

# ----------------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_GRAY=$'\033[90m'; C_RESET=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_GRAY=""; C_RESET=""
fi

banner() {
    local line
    line=$(printf '=%.0s' $(seq 1 64))
    printf '\n%s%s%s\n' "$C_CYAN" "$line" "$C_RESET"
    printf '%s  %s%s\n' "$C_CYAN" "$1" "$C_RESET"
    printf '%s%s%s\n' "$C_CYAN" "$line" "$C_RESET"
}
step() { printf '\n%s[%s] %s%s\n' "$C_YELLOW" "$1" "$2" "$C_RESET"; }
ok()   { printf '%s  [OK]   %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
info() { printf '%s  [..]   %s%s\n' "$C_GRAY" "$*" "$C_RESET"; }
warn() { printf '%s  [!!]   %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
fail() { printf '%s  [ERR]  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; }

show_proxy_hint() {
    cat <<'EOF'

  Si vous etes derriere un proxy d'entreprise, definissez avant de relancer :
      export HTTPS_PROXY="http://proxy.entreprise.local:8080"
      export HTTP_PROXY="$HTTPS_PROXY"
  Certificat interne (inspection SSL) :  export PIP_CERT=/chemin/ca-entreprise.pem
  Depot PyPI interne (Artifactory/Nexus) :  export PIP_INDEX_URL="https://.../simple"
  Details : docs/INSTALLATION.md (section Troubleshooting)

EOF
}

# ----------------------------------------------------------------------------
# Detection de Python
# ----------------------------------------------------------------------------
# Affiche "major minor patch bits" ou rien si l'executable est inutilisable.
python_version_info() {
    local exe="$1"
    [ -x "$exe" ] || command -v "$exe" >/dev/null 2>&1 || return 1
    "$exe" -c 'import sys, struct; print("%d %d %d %d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2], struct.calcsize("P") * 8))' 2>/dev/null
}

python_supported() {
    local info major minor bits
    info=$(python_version_info "$1") || return 1
    [ -n "$info" ] || return 1
    read -r major minor _ bits <<<"$info"
    [ "$major" -eq 3 ] && [ "$minor" -ge "$PYTHON_MIN_MINOR" ] && [ "$minor" -le "$PYTHON_MAX_MINOR" ] && [ "$bits" -eq 64 ]
}

# Premier Python 3.10-3.12 (64 bits) trouve ; preference 3.11 > 3.12 > 3.10.
# Argument 2 optionnel : versions mineures a privilegier (ex: "10 11", celles
# couvertes par le wheelhouse) ; elles passent devant toutes les autres.
find_python() {
    local root="$1" preferred="${2:-}" name exe
    local -a candidates=()
    for name in python3.11 python3.12 python3.10 python3 python; do
        exe=$(command -v "$name" 2>/dev/null) && candidates+=("$exe")
    done
    # Emplacements classiques (pyenv, Homebrew, uv, conda, /usr/local)
    for exe in \
        "$HOME"/.pyenv/versions/3.11.*/bin/python3 "$HOME"/.pyenv/versions/3.12.*/bin/python3 "$HOME"/.pyenv/versions/3.10.*/bin/python3 \
        /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.10 \
        /usr/local/bin/python3.11 /usr/local/bin/python3.12 /usr/local/bin/python3.10 \
        "$HOME"/.local/share/uv/python/cpython-3.11*/bin/python3 "$HOME"/.local/share/uv/python/cpython-3.12*/bin/python3 \
        "$HOME"/miniconda3/bin/python3 "$HOME"/anaconda3/bin/python3 \
        "$root"/.python/bin/python3; do
        [ -x "$exe" ] && candidates+=("$exe")
    done

    local best="" best_rank=99 rank info minor
    # ${arr[@]+"${arr[@]}"} : tableau vide compatible bash 3.2 (macOS) sous set -u
    for exe in ${candidates[@]+"${candidates[@]}"}; do
        python_supported "$exe" || continue
        info=$(python_version_info "$exe"); read -r _ minor _ _ <<<"$info"
        case "$minor" in 11) rank=0 ;; 12) rank=1 ;; *) rank=2 ;; esac
        if [ -n "$preferred" ]; then
            case " $preferred " in *" $minor "*) ;; *) rank=$((rank + 10)) ;; esac
        fi
        if [ "$rank" -lt "$best_rank" ]; then best="$exe"; best_rank="$rank"; fi
    done
    [ -n "$best" ] && printf '%s\n' "$best"
}

python_install_hint() {
    cat <<'EOF'

  Installez Python 3.11 (64 bits) sans droits administrateur, au choix :
    - uv (recommande, aucun admin) :
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv python install 3.11
          ./setup.sh --python "$(uv python find 3.11)"
    - pyenv :  pyenv install 3.11 && ./setup.sh --python "$(pyenv prefix 3.11)/bin/python3"
    - macOS :  brew install python@3.11   (ou l'installeur python.org "pour moi uniquement")
    - Debian/Ubuntu (avec sudo) :  sudo apt install python3.11 python3.11-venv
  puis relancez ./setup.sh
EOF
}

# ----------------------------------------------------------------------------
# Environnement virtuel / reseau local / processus
# ----------------------------------------------------------------------------
venv_python() {
    local exe="$1/.venv/bin/python"
    [ -x "$exe" ] && printf '%s\n' "$exe"
}

# ----------------------------------------------------------------------------
# Wheelhouse (installation hors-ligne)
# ----------------------------------------------------------------------------
# Versions mineures de Python couvertes par un wheelhouse ("10 11 12"), d'apres
# les tags cp3XY-cp3XY des wheels compilees (numpy, pandas, pydantic-core...).
# Les wheels pures (py3-none-any) et abi3 conviennent a toutes les versions.
# Vide si le dossier ne contient aucune wheel compilee. Retourne toujours 0.
wheelhouse_python_minors() {
    local dir="$1"
    [ -d "$dir" ] || return 0
    ls "$dir" 2>/dev/null | sed -n -E 's/^.*-cp3([0-9]+)-cp3[0-9]+-.*\.whl$/\1/p' | sort -un | tr '\n' ' ' | sed 's/ $//'
    return 0
}

# "10 12" -> "3.10, 3.12"
format_python_minors() {
    local out="" m
    for m in $1; do out="$out, 3.$m"; done
    printf '%s\n' "${out#, }"
}

# Familles de plateformes presentes dans un wheelhouse (ex: "linux-x86_64 macos-arm64").
wheelhouse_platforms() {
    local dir="$1" names out=""
    [ -d "$dir" ] || return 0
    names=$(ls "$dir" 2>/dev/null | grep -E '\-cp3[0-9]+-cp3[0-9]+-' || true)
    case "$names" in *win_amd64*) out="$out windows-x64" ;; esac
    case "$names" in *manylinux*x86_64*) out="$out linux-x86_64" ;; esac
    # macOS : seules les wheels mono-architecture qualifient (ni universal2, ni les
    # noms multi-tags comme macosx_10_15_x86_64.macosx_11_0_arm64 d'orjson)
    # (pas de grep -q : sous pipefail une sortie anticipee provoquerait un SIGPIPE)
    [ -n "$(printf '%s\n' "$names" | grep -E 'macosx[^-]*arm64' | grep -v x86_64)" ] && out="$out macos-arm64"
    [ -n "$(printf '%s\n' "$names" | grep -E 'macosx[^-]*x86_64' | grep -v arm64)" ] && out="$out macos-x86_64"
    printf '%s\n' "${out# }"
    return 0
}

# Plateforme courante dans le meme vocabulaire (pour comparer avec wheelhouse_platforms).
current_platform() {
    local machine
    machine=$(uname -m 2>/dev/null | tr '[:upper:]' '[:lower:]')
    case "$(uname -s 2>/dev/null)" in
        Darwin) case "$machine" in arm64|aarch64) echo "macos-arm64" ;; *) echo "macos-x86_64" ;; esac ;;
        Linux)  case "$machine" in x86_64|amd64) echo "linux-x86_64" ;; *) echo "linux-$machine" ;; esac ;;
        *)      echo "$(uname -s)-$machine" ;;
    esac
}

python_has_module() { "$1" -c "import $2" >/dev/null 2>&1; }

# Requete HTTP locale sans proxy ; vrai si le serveur repond (meme 4xx/5xx).
http_up() {
    local url="$1" code
    if command -v curl >/dev/null 2>&1; then
        code=$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" 2>/dev/null) || return 1
        [ -n "$code" ] && [ "$code" != "000" ]
    else
        "${VENV_PYTHON:-python3}" - "$url" <<'EOF' >/dev/null 2>&1
import sys, urllib.request, urllib.error
req = urllib.request.Request(sys.argv[1])
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    opener.open(req, timeout=3); sys.exit(0)
except urllib.error.HTTPError:
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF
    fi
}

wait_http_ready() {
    local url="$1" timeout="${2:-60}" waited=0
    while [ "$waited" -lt "$timeout" ]; do
        http_up "$url" && return 0
        sleep 1; waited=$((waited + 1))
    done
    return 1
}

# PIDs des processus en ecoute sur un port (lsof, ss ou fuser selon disponibilite).
# Retourne toujours 0 (liste vide = port libre) : utilisable sous `set -e -o pipefail`.
port_listeners() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u
    elif command -v ss >/dev/null 2>&1; then
        ss -ltnpH "sport = :$port" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u
    elif command -v fuser >/dev/null 2>&1; then
        fuser -n tcp "$port" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | sort -u
    fi
    return 0
}

port_in_use() { [ -n "$(port_listeners "$1")" ]; }

# Lit une cle du .env (KEY=value, commentaires et guillemets ignores) ; sinon defaut.
dotenv_get() {
    local file="$1" key="$2" default="$3" value
    if [ -f "$file" ]; then
        value=$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$file" | tail -n1 | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    fi
    printf '%s\n' "${value:-$default}"
}

dotenv_get_int() {
    local v
    v=$(dotenv_get "$1" "$2" "$3")
    case "$v" in ''|*[!0-9]*) printf '%s\n' "$3" ;; *) printf '%s\n' "$v" ;; esac
}

# Termine un processus et ses descendants (parent d'abord : un superviseur
# comme `uvicorn --reload` ne peut pas relancer son worker entre-temps).
kill_tree() {
    local pid="$1" children pgid
    [ -n "$pid" ] || return 0
    kill -0 "$pid" 2>/dev/null || return 0
    children=$(pgrep -P "$pid" 2>/dev/null || true)
    pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ -n "$pgid" ] && [ "$pgid" = "$pid" ]; then
        # chef de groupe (run_logged.py) : tout le groupe d'un coup
        kill -TERM -- "-$pgid" 2>/dev/null || true
    fi
    kill -TERM "$pid" 2>/dev/null || true
    for c in $children; do kill_tree "$c"; done
}
