#!/usr/bin/env bash
# =============================================================================
# Lance le Power Market Intelligence Agent (backend FastAPI + frontend Streamlit)
# sous Linux / macOS. Equivalent de start.ps1 (Windows).
#
#   ./start.sh                       backend + frontend en arriere-plan, logs dans ./logs/
#   ./start.sh --foreground          reste attache : Ctrl+C arrete les deux services
#   ./start.sh --backend-port 8010 --frontend-port 8511
#   ./start.sh --backend-only | --frontend-only | --no-browser | --no-reload
#
# Les ports sont lus dans .env (BACKEND_PORT / FRONTEND_PORT) sauf option explicite.
# Les services ecoutent uniquement sur 127.0.0.1. Arret : ./stop.sh
# =============================================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/unix/common.sh
. "$ROOT/scripts/unix/common.sh"

BACKEND_PORT=0; FRONTEND_PORT=0
BACKEND_ONLY=0; FRONTEND_ONLY=0; NO_BROWSER=0; NO_RELOAD=0; FOREGROUND=0
while [ $# -gt 0 ]; do
    case "$1" in
        --backend-port) BACKEND_PORT="${2:-0}"; shift ;;
        --backend-port=*) BACKEND_PORT="${1#*=}" ;;
        --frontend-port) FRONTEND_PORT="${2:-0}"; shift ;;
        --frontend-port=*) FRONTEND_PORT="${1#*=}" ;;
        --backend-only) BACKEND_ONLY=1 ;;
        --frontend-only) FRONTEND_ONLY=1 ;;
        --no-browser) NO_BROWSER=1 ;;
        --no-reload) NO_RELOAD=1 ;;
        --foreground|-f) FOREGROUND=1 ;;
        -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "Option inconnue : $1 (voir --help)"; exit 2 ;;
    esac
    shift
done

banner "Power Market Intelligence Agent - Demarrage (Linux / macOS)"

VENV_PYTHON=$(venv_python "$ROOT" || true)
if [ -z "$VENV_PYTHON" ]; then
    fail "Environnement virtuel introuvable (.venv). Lancez d'abord :  ./setup.sh"
    exit 1
fi
export VENV_PYTHON
if ! python_has_module "$VENV_PYTHON" uvicorn || ! python_has_module "$VENV_PYTHON" streamlit; then
    fail "Dependances manquantes dans .venv. Relancez :  ./setup.sh"
    exit 1
fi

ENV_FILE="$ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    info ".env cree a partir de .env.example"
fi
[ "$BACKEND_PORT" -gt 0 ] 2>/dev/null || BACKEND_PORT=$(dotenv_get_int "$ENV_FILE" BACKEND_PORT 8000)
[ "$FRONTEND_PORT" -gt 0 ] 2>/dev/null || FRONTEND_PORT=$(dotenv_get_int "$ENV_FILE" FRONTEND_PORT 8501)

LOG_DIR="$ROOT/logs"; mkdir -p "$LOG_DIR"
PID_FILE="$LOG_DIR/pids.env"
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

START_BACKEND=$((1 - FRONTEND_ONLY))
START_FRONTEND=$((1 - BACKEND_ONLY))

# --- Ports ---------------------------------------------------------------------
if [ "$START_BACKEND" -eq 1 ] && port_in_use "$BACKEND_PORT"; then
    if http_up "$BACKEND_URL/health"; then
        warn "Un backend repond deja sur le port $BACKEND_PORT : il sera reutilise (./stop.sh pour l'arreter)."
        START_BACKEND=0
    else
        fail "Le port $BACKEND_PORT est occupe par un autre programme. Utilisez --backend-port <autre> ou ./stop.sh"
        exit 1
    fi
fi
if [ "$START_FRONTEND" -eq 1 ] && port_in_use "$FRONTEND_PORT"; then
    if http_up "http://127.0.0.1:$FRONTEND_PORT/_stcore/health"; then
        warn "Un frontend repond deja sur le port $FRONTEND_PORT : il sera reutilise."
        START_FRONTEND=0
    else
        fail "Le port $FRONTEND_PORT est occupe. Utilisez --frontend-port <autre> ou ./stop.sh"
        exit 1
    fi
fi

# --- Environnement transmis aux services ---------------------------------------
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
export BACKEND_URL BACKEND_PORT FRONTEND_PORT
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false STREAMLIT_SERVER_HEADLESS=true
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}localhost,127.0.0.1"
export no_proxy="$NO_PROXY"

BACKEND_ARGS=(-m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT")
[ "$NO_RELOAD" -eq 1 ] || BACKEND_ARGS+=(--reload)
FRONTEND_ARGS=(-m streamlit run app.py --server.port "$FRONTEND_PORT" --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false)

BACKEND_PID=""; FRONTEND_PID=""

# Lance un service en arriere-plan via run_logged.py (stdout+stderr fusionnes dans
# logs/<service>.log). run_logged.py se detache dans sa propre session (os.setsid)
# pour survivre a la fermeture du terminal, sur Linux comme sur macOS.
# Le sous-shell est entierement redirige : aucun descripteur du terminal n'est
# herite, sinon `$(start_service ...)` attendrait la fin du service.
start_service() {  # name workdir args...
    local name="$1" workdir="$2"; shift 2
    local log="$LOG_DIR/$name.log"
    ( cd "$workdir" && exec "$VENV_PYTHON" "$ROOT/scripts/run_logged.py" "$log" "$@" ) >/dev/null 2>&1 </dev/null &
    echo $!
}

if [ "$START_BACKEND" -eq 1 ]; then
    step "1/2" "Backend FastAPI  ->  $BACKEND_URL"
    BACKEND_PID=$(start_service backend "$ROOT/backend" "${BACKEND_ARGS[@]}")
    ok "Backend demarre (PID $BACKEND_PID) - log : $LOG_DIR/backend.log"
    info "Attente du backend ($BACKEND_URL/health)..."
    if wait_http_ready "$BACKEND_URL/health" 90; then
        ok "Backend pret : $BACKEND_URL/docs"
    else
        warn "Le backend ne repond pas encore. Consultez $LOG_DIR/backend.log"
    fi
else
    step "1/2" "Backend : non demarre (deja actif ou --frontend-only)"
fi

if [ "$START_FRONTEND" -eq 1 ]; then
    step "2/2" "Frontend Streamlit  ->  $FRONTEND_URL"
    FRONTEND_PID=$(start_service frontend "$ROOT/frontend" "${FRONTEND_ARGS[@]}")
    ok "Frontend demarre (PID $FRONTEND_PID) - log : $LOG_DIR/frontend.log"
    info "Attente du frontend..."
    if wait_http_ready "http://127.0.0.1:$FRONTEND_PORT/_stcore/health" 90; then
        ok "Frontend pret : $FRONTEND_URL"
    else
        warn "Le frontend ne repond pas encore. Consultez $LOG_DIR/frontend.log"
    fi
else
    step "2/2" "Frontend : non demarre (deja actif ou --backend-only)"
fi

# --- Enregistrement des PIDs (pour stop.sh) ------------------------------------
OLD_BACKEND=$(dotenv_get "$PID_FILE" backend ""); OLD_FRONTEND=$(dotenv_get "$PID_FILE" frontend "")
{
    echo "backend=${BACKEND_PID:-$OLD_BACKEND}"
    echo "frontend=${FRONTEND_PID:-$OLD_FRONTEND}"
    echo "backend_port=$BACKEND_PORT"
    echo "frontend_port=$FRONTEND_PORT"
} > "$PID_FILE"

echo
banner "Application demarree"
printf '  %sFrontend (Streamlit) :  %s%s\n' "$C_CYAN" "$FRONTEND_URL" "$C_RESET"
echo "  API Swagger          :  http://localhost:$BACKEND_PORT/docs"
echo "  Health               :  http://localhost:$BACKEND_PORT/health"
echo "  Logs                 :  $LOG_DIR/backend.log  |  $LOG_DIR/frontend.log"
echo "  Arret                :  ./stop.sh"
echo

if [ "$NO_BROWSER" -eq 0 ] && [ "$BACKEND_ONLY" -eq 0 ]; then
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then open "$FRONTEND_URL" >/dev/null 2>&1 || true
    fi
fi

if [ "$FOREGROUND" -eq 1 ]; then
    info "Mode --foreground : Ctrl+C pour arreter les services."
    # shellcheck disable=SC2064
    trap 'kill "$!" 2>/dev/null; echo; "$ROOT/stop.sh"; exit 0' INT TERM
    while :; do sleep 3600 & wait "$!"; done
fi
