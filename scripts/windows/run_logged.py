"""
Lance une commande Python en redirigeant stdout + stderr (fusionnes) vers un
fichier de log. Utilise par `start.ps1 -Background`.

    python scripts\\windows\\run_logged.py <fichier.log> -m uvicorn app.main:app ...

Pourquoi ce wrapper plutot qu'une redirection PowerShell ?
- uvicorn / streamlit ecrivent leurs logs sur stderr ;
- sous Windows PowerShell 5.1, `2>&1` transforme chaque ligne stderr d'un
  programme natif en ErrorRecord (format multi-lignes illisible) ;
- Start-Process ne sait pas rediriger stdout et stderr vers le meme fichier.
Ici la fusion est faite au niveau des handles du systeme : le log est brut,
ordonne, et en UTF-8.
"""
import os
import signal
import subprocess
import sys
import time


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    log_path = os.path.abspath(sys.argv[1])
    cmd = [sys.executable] + sys.argv[2:]
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    creationflags = 0
    if sys.platform == "win32":
        # Pas de fenetre console pour le processus fils (mode arriere-plan)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    with open(log_path, "ab", buffering=0) as log:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"\n===== {stamp} | cwd={os.getcwd()} | {' '.join(cmd)} =====\n".encode("utf-8"))
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            creationflags=creationflags,
        )

        def _forward(signum, _frame):  # arret propre si le wrapper recoit SIGTERM / Ctrl+C
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _forward)
            except Exception:  # noqa: BLE001
                pass

        try:
            return proc.wait()
        except KeyboardInterrupt:
            _forward(None, None)
            return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
