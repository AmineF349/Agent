#!/usr/bin/env bash
# =============================================================================
# Arrete le backend et le frontend lances par start.sh. Equivalent de stop.ps1.
#
#   ./stop.sh
#   ./stop.sh --backend-port 8010 --frontend-port 8511
#
# - termine les processus enregistres dans logs/pids.env (et leurs enfants),
# - libere les ports du projet s'ils sont encore tenus par un python du .venv.
#   Aucun autre programme n'est touche.
# =============================================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
# shellcheck source=scripts/unix/common.sh
. "$ROOT/scripts/unix/common.sh"

BACKEND_PORT=0; FRONTEND_PORT=0
while [ $# -gt 0 ]; do
    case "$1" in
        --backend-port) BACKEND_PORT="${2:-0}"; shift ;;
        --backend-port=*) BACKEND_PORT="${1#*=}" ;;
        --frontend-port) FRONTEND_PORT="${2:-0}"; shift ;;
        --frontend-port=*) FRONTEND_PORT="${1#*=}" ;;
        -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "Option inconnue : $1"; exit 2 ;;
    esac
    shift
done

banner "Power Market Intelligence Agent - Arret"

PID_FILE="$ROOT/logs/pids.env"
STOPPED=0

is_project_process() {  # vrai si le processus est un python du .venv ou notre run_logged.py
    local pid="$1" cmd
    cmd=$(ps -o command= -p "$pid" 2>/dev/null || ps -o args= -p "$pid" 2>/dev/null || true)
    case "$cmd" in
        *"$ROOT/.venv/"*|*"$ROOT/.python/"*|*run_logged.py*) return 0 ;;
        *) return 1 ;;
    esac
}

stop_pid() {  # name pid
    local name="$1" pid="$2"
    [ -n "$pid" ] || return 0
    kill -0 "$pid" 2>/dev/null || return 0
    if ! is_project_process "$pid"; then
        warn "PID $pid ($name) n'est plus un processus du projet - ignore."
        return 0
    fi
    info "Arret $name (PID $pid)"
    kill_tree "$pid"
    STOPPED=$((STOPPED + 1))
}

# 1. Processus enregistres par start.sh
if [ -f "$PID_FILE" ]; then
    stop_pid backend "$(dotenv_get "$PID_FILE" backend "")"
    stop_pid frontend "$(dotenv_get "$PID_FILE" frontend "")"
    [ "$BACKEND_PORT" -gt 0 ] 2>/dev/null || BACKEND_PORT=$(dotenv_get_int "$PID_FILE" backend_port 0)
    [ "$FRONTEND_PORT" -gt 0 ] 2>/dev/null || FRONTEND_PORT=$(dotenv_get_int "$PID_FILE" frontend_port 0)
    rm -f "$PID_FILE"
fi
[ "$BACKEND_PORT" -gt 0 ] 2>/dev/null || BACKEND_PORT=$(dotenv_get_int "$ROOT/.env" BACKEND_PORT 8000)
[ "$FRONTEND_PORT" -gt 0 ] 2>/dev/null || FRONTEND_PORT=$(dotenv_get_int "$ROOT/.env" FRONTEND_PORT 8501)

# Laisse le temps aux processus de se terminer proprement avant de verifier les ports
sleep 1

# 2. Processus du projet encore en ecoute sur les ports
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    for pid in $(port_listeners "$port"); do
        if is_project_process "$pid"; then
            info "Liberation du port $port (PID $pid)"
            kill_tree "$pid"
            STOPPED=$((STOPPED + 1))
        else
            warn "Port $port occupe par un processus hors projet (PID $pid) - non arrete."
        fi
    done
done

# 3. Derniere chance : SIGKILL sur ce qui resisterait encore (apres 3 s)
sleep 2
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    for pid in $(port_listeners "$port"); do
        if is_project_process "$pid"; then
            warn "PID $pid ne repond pas a SIGTERM : SIGKILL"
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
done

if [ "$STOPPED" -gt 0 ]; then ok "$STOPPED processus arrete(s)."; else ok "Aucun processus a arreter."; fi
