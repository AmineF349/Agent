# Installation - Power Market Intelligence Agent

Le projet s'installe et se lance **100 % nativement** : deux processus Python (FastAPI + Streamlit)
dans un seul environnement virtuel `.venv`. **Pas de Docker, pas de base de données, pas de droits
administrateur, pas de compilation.**

## Prérequis

- Python 3.10, 3.11 ou 3.12 – 64 bits (recommandé 3.11). Python 3.13+ non supporté (pas de wheels
  précompilées pour numpy/pandas/pydantic aux versions épinglées).
- Git.
- 4 Go de RAM minimum, 8 Go recommandé ; ~1 Go d'espace disque pour le `.venv`.
- Accès à https://pypi.org (directement ou via le proxy d'entreprise) lors de l'installation.
- Aucune base de données ni service externe : le projet n'utilise ni PostgreSQL, ni Redis, ni Docker.
- VS Code (recommandé, voir [VSCODE_GUIDE.md](VSCODE_GUIDE.md)).

## Option 1 : Windows – sans droits admin (recommandé sur poste d'entreprise)

```powershell
git clone https://github.com/AmineF349/Agent.git
cd Agent
.\setup.ps1     # détecte/installe Python 3.11 (sans admin), crée .venv, installe les dépendances, crée .env
.\start.ps1     # backend :8000 + frontend :8501, ouvre le navigateur
.\stop.ps1      # arrêt
.\test.ps1      # pytest
```

Si PowerShell bloque les scripts : `powershell -ExecutionPolicy Bypass -File .\setup.ps1`
ou double-clic sur `setup.cmd` / `start.cmd`.

Guide complet (options, proxy d'entreprise, Python absent, dépannage) : [WINDOWS_SETUP.md](WINDOWS_SETUP.md).

## Option 2 : Linux / macOS – scripts `.sh`

```bash
git clone https://github.com/AmineF349/Agent.git
cd Agent
./setup.sh      # détecte Python 3.10-3.12, crée .venv, installe les dépendances, crée .env
./start.sh      # backend :8000 + frontend :8501 en arrière-plan, ouvre le navigateur
./stop.sh       # arrêt
./test.sh       # pytest
```

| Script | Rôle et options |
|--------|-----------------|
| `setup.sh` | `--python /chemin/python3.11` (interpréteur explicite), `--dev` (pytest/black/flake8), `--force` (recrée le `.venv`), `--offline` (dépendances lues dans `./wheelhouse/`, aucun accès réseau) |
| `start.sh` | Lance les deux services en arrière-plan (logs dans `logs/backend.log` et `logs/frontend.log`, PIDs dans `logs/pids.env`). Options : `--foreground` (Ctrl+C arrête tout), `--backend-port N`, `--frontend-port N`, `--no-browser`, `--backend-only`, `--frontend-only`, `--no-reload` |
| `stop.sh` | Arrête les processus lancés par `start.sh` et libère les ports du projet (uniquement s'ils sont tenus par un python du `.venv`) |
| `test.sh` | `pytest tests/ -v` depuis `backend/` ; arguments transmis à pytest (`./test.sh -k baseload -x`) |

Les services sont détachés du terminal (`setsid`) : vous pouvez fermer la fenêtre, ils continuent
de tourner jusqu'à `./stop.sh`. Relancer `./start.sh` alors qu'ils tournent ne provoque pas d'erreur
(les services sains sont réutilisés).

### Pas de Python 3.10-3.12 sur la machine ?

Sans droits root, le plus simple est [uv](https://docs.astral.sh/uv/) ou pyenv :

```bash
# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11
./setup.sh --python "$(uv python find 3.11)"

# pyenv
pyenv install 3.11 && ./setup.sh --python "$(pyenv prefix 3.11)/bin/python3"
```

Avec des droits : `brew install python@3.11` (macOS) ou `sudo apt install python3.11 python3.11-venv`
(Debian/Ubuntu – le module `venv` est packagé séparément).

## Option 3 : Manuel (toutes plateformes)

Un seul environnement virtuel à la racine pour le backend et le frontend (`requirements.txt`
regroupe les deux et ne contient que des wheels précompilées ; `constraints.txt` fige les
dépendances indirectes).

```bash
git clone https://github.com/AmineF349/Agent.git
cd Agent
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell : .\.venv\Scripts\Activate.ps1
pip install --only-binary :all: -r requirements.txt -c constraints.txt
cp .env.example .env               # Windows : Copy-Item .env.example .env
python scripts/check_install.py    # vérification (imports backend/frontend, chemins, .env)
```

## Installation hors-ligne (poste sans accès à PyPI)

Les dépendances peuvent être préparées sur **n'importe quelle machine connectée** (l'OS et le
Python cibles sont des paramètres, pas ceux de la machine qui télécharge) :

```bash
python scripts/make_wheelhouse.py                                  # pour cette machine
python scripts/make_wheelhouse.py --platform win_amd64 --python-version 3.11 --zip   # pour un poste Windows
python scripts/make_wheelhouse.py --all-platforms                  # tout (≈ 2 Go)
# plateformes : win_amd64, linux_x86_64, linux_aarch64, macos_arm64, macos_x86_64
```

Copiez le dossier `wheelhouse/` (ou `wheelhouse.zip` décompressé) à la racine du projet sur le
poste cible, puis `./setup.sh --offline` ou `.\setup.ps1 -Offline` : pip travaille en
`--no-index --find-links wheelhouse`, sans aucun accès réseau. Python 3.10-3.12 doit déjà être
présent sur le poste cible. Un `wheelhouse/` présent est aussi utilisé en priorité par une
installation normale (PyPI ne sert qu'aux paquets manquants).

## Reproductibilité des dépendances (`constraints.txt`)

- `requirements.txt` / `requirements-dev.txt` : les dépendances **directes**, épinglées (source de vérité).
- `constraints.txt` : **toutes** les dépendances (directes + indirectes) figées pour Windows, Linux et
  macOS, Python 3.10 à 3.12, en une seule résolution « universelle » (marqueurs d'environnement).
  Généré par `python scripts/update_constraints.py` (utilise [uv](https://docs.astral.sh/uv/),
  installé automatiquement dans le venv si absent) ; `--upgrade` remonte les indirectes,
  `--check` (utilisé par la CI) vérifie qu'il est à jour.
- Toutes les versions ont été vérifiées disponibles en wheel précompilée (cp310-cp312 ;
  win_amd64, manylinux x86_64, macOS x86_64 et arm64).

Pour changer une dépendance : modifiez `requirements.txt`, lancez `python scripts/update_constraints.py`,
puis `./setup.sh` / `.\setup.ps1` (et régénérez le wheelhouse si vous en distribuez un).

### Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

# Vérifier
curl http://localhost:8000/health
# Docs : http://localhost:8000/docs
```

Le backend charge automatiquement le `.env` de la racine du dépôt et résout ses chemins
(`knowledge_base/`, `backend/generated/`) de façon absolue : il peut être lancé depuis
n'importe quel répertoire (`uvicorn app.main:app` depuis `backend/`, ou
`PYTHONPATH=backend uvicorn app.main:app` depuis la racine).

### Frontend

```bash
cd frontend
BACKEND_URL=http://localhost:8000 streamlit run app.py --server.port 8501 --server.address 127.0.0.1
# Windows PowerShell : $env:BACKEND_URL = "http://localhost:8000"; streamlit run app.py --server.port 8501
# Ouvrir http://localhost:8501
```

### Variables d'environnement

Voir `.env.example`:

- **Sans clé**: fonctionne 100% avec fallback local + APIs publiques gratuites
- **Avec LLM** (optionnel, pour réponses plus riches):
  - `OPENAI_API_KEY=sk-...` (https://platform.openai.com/api-keys)
  - Ou `ANTHROPIC_API_KEY=sk-ant-...` (https://console.anthropic.com/settings/keys)
  - Ou Azure OpenAI
- **ENTSO-E** (optionnel, gratuit):
  - Créer compte https://transparency.entsoe.eu/
  - Générer token
  - `ENTSOE_API_KEY=...`
- **Ports / URL** : `BACKEND_PORT`, `FRONTEND_PORT` (lus par les scripts de lancement), `BACKEND_URL`
  (positionnée automatiquement par `start.ps1` / `start.sh` pour le frontend)
- **Chemins** (optionnel) : `GENERATED_DIR`, `KNOWLEDGE_BASE_DIR`, `DATA_SAMPLES_DIR`, `PMIA_ENV_FILE`

## APIs Publiques Gratuites Utilisées

- **Energy-Charts.info**: https://api.energy-charts.info - Prix day-ahead EU, sans clé, 100% gratuit (Fraunhofer ISE)
- **Open-Meteo**: https://open-meteo.com/ - Météo, vent, solaire, sans clé, 100% gratuit
- **ENTSO-E**: https://transparency.entsoe.eu/ - Optionnel, clé gratuite après inscription

Si ces APIs sont inaccessibles (proxy, hors-ligne), le backend bascule automatiquement sur des données
mock : l'application reste 100 % fonctionnelle.

## Vérification Installation

```bash
# Backend health
curl http://localhost:8000/health

# Doit retourner:
# {"status":"ok","version":"1.0.0","llm_available":false,"public_apis":{"energy_charts":true,"open_meteo":true},...}

# Frontend
curl http://localhost:8501/_stcore/health     # -> ok

# Tests (30 tests)
./test.sh          # Linux / macOS
.\test.ps1         # Windows
```

## Troubleshooting

**Windows (proxy, ExecutionPolicy, Python absent, ports occupés) :** voir [WINDOWS_SETUP.md – Dépannage](WINDOWS_SETUP.md#6-dépannage).

**`setup.sh` : « Aucun Python 3.10 - 3.12 (64 bits) trouvé »**
- Installez Python 3.11 via uv / pyenv / brew (voir plus haut) puis `./setup.sh --python <chemin>`.
- Python 3.13+ n'est pas utilisable : les wheels des versions épinglées n'existent pas.

**`setup.sh` : « ensurepip is not available » à la création du venv (Debian/Ubuntu)**
- `sudo apt install python3.X-venv`, ou sans droits : installez Python via uv.

**`pip install` échoue (proxy d'entreprise)**
- `export HTTPS_PROXY=http://proxy:port` (et `HTTP_PROXY`) puis relancez `./setup.sh` ;
  si le proxy réécrit les certificats : `pip config set global.trusted-host "pypi.org files.pythonhosted.org"`.
- Aucun accès à PyPI possible : voir « Installation hors-ligne » ci-dessus.

**Backend ne démarre pas:**
- Vérifier port 8000 libre: `lsof -i :8000` (Linux/macOS) / `Get-NetTCPConnection -LocalPort 8000` (Windows), ou simplement `./stop.sh` / `.\stop.ps1`
- Vérifier PYTHONPATH: `export PYTHONPATH=backend` (ou lancer depuis `backend/`)
- Logs: `logs/backend.log` (`start.sh` ou `start.ps1 -Background`) ou la fenêtre backend (`start.ps1`)

**Frontend ne se connecte pas au backend:**
- Vérifier la variable d'environnement `BACKEND_URL` : `http://localhost:8000` (positionnée par `start.ps1` / `start.sh`)
- Derrière un proxy d'entreprise : `NO_PROXY=localhost,127.0.0.1` (positionnée par les scripts de lancement)
- Vérifier CORS_ORIGINS

**APIs publiques down:**
- Normal, fallback mock automatique, 100% fonctionnel
- Vérifier https://api.energy-charts.info/price?bzn=FR&year=2024 dans navigateur

**LLM non disponible:**
- Normal si pas de clé, fallback local activé, 100% fonctionnel
- Pour activer, ajouter clé dans .env

**Désinstallation**
- `./stop.sh` (ou `.\stop.ps1`) puis supprimer le dossier du dépôt : rien n'est installé ailleurs
  (le `.venv`, `.env`, `logs/` et `backend/generated/` sont dans le dépôt).

## Structure Projet

```
.
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI)
│   │   ├── core/ (config, logging, paths)
│   │   ├── api/routes/ (6 modules)
│   │   ├── services/ (logique métier)
│   │   ├── data/connectors/ (Energy-Charts, Open-Meteo, ENTSO-E, Mock)
│   │   └── agent/ (LLM provider, LangGraph)
│   ├── tests/
│   └── data_samples/
├── frontend/
│   ├── app.py (Streamlit main)
│   ├── pages/ (6 pages)
│   └── components/
├── knowledge_base/
│   ├── concepts/ (capture_rate, baseload, BESS...)
│   └── models/ (AFRY, Aurora)
├── docs/
├── scripts/ (check_install.py, run_logged.py, make_wheelhouse.py, update_constraints.py,
│             windows/common.ps1, unix/common.sh)
├── setup.ps1 / start.ps1 / stop.ps1 / test.ps1 (Windows)
├── setup.sh / start.sh / stop.sh / test.sh (Linux / macOS)
├── requirements.txt / requirements-dev.txt / constraints.txt
└── .env.example
```

## Prochaines Étapes

1. Lire `docs/WINDOWS_SETUP.md` (Windows) et `docs/VSCODE_GUIDE.md` pour dev dans VS Code
2. Lire `docs/USER_GUIDE.md` pour utilisation
3. Lire `ARCHITECTURE.md` pour architecture
4. Explorer `http://localhost:8000/docs` pour API
5. Tester avec `backend/data_samples/sample_prices.csv`

## Support

- README.md pour overview
- ROADMAP.md pour évolutions
- Ouvrir issue GitHub
