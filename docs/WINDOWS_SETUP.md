# Installation Windows sans Docker (poste d'entreprise, sans droits admin)

Ce guide décrit l'installation et le lancement **100 % natifs** du Power Market
Intelligence Agent sous Windows 10/11 :

- **sans Docker Desktop** (bloqué par la DSI),
- **sans droits administrateur**,
- **sans compilation** (aucun Visual Studio Build Tools),
- **sans base de données ni service externe** (pas de PostgreSQL, pas de Redis).

L'application est composée de deux processus Python qui tournent sur votre
poste et communiquent en HTTP local :

| Service  | Technologie        | Port par défaut | URL                          |
|----------|--------------------|-----------------|------------------------------|
| Backend  | FastAPI + uvicorn  | 8000            | http://localhost:8000/docs   |
| Frontend | Streamlit          | 8501            | http://localhost:8501        |

Les deux écoutent uniquement sur `127.0.0.1` : rien n'est exposé sur le réseau,
aucune règle de pare-feu n'est nécessaire.

---

## TL;DR

```powershell
git clone https://github.com/AmineF349/Agent.git
cd Agent
.\setup.ps1      # une seule fois (2 à 5 minutes)
.\start.ps1      # à chaque utilisation -> ouvre http://localhost:8501
.\stop.ps1       # pour tout arrêter
```

Si PowerShell refuse d'exécuter les scripts, double-cliquez sur `setup.cmd`
puis `start.cmd`, ou lancez :

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

---

## 1. Prérequis

| Composant | Requis | Remarque |
|-----------|--------|----------|
| Windows 10 / 11 64 bits | oui | |
| PowerShell 5.1 (inclus dans Windows) ou PowerShell 7 | oui | aucun module supplémentaire |
| **Python 3.10, 3.11 ou 3.12 (64 bits)** | oui | **3.11 recommandé.** Python 3.13+ n'est pas supporté (pas de wheels pour numpy 1.26 / pandas 2.2). Si absent, `setup.ps1` propose de l'installer sans admin (voir §3). |
| Git | recommandé | sinon téléchargez le ZIP du dépôt |
| Accès HTTPS à `pypi.org` / `files.pythonhosted.org` | oui (installation uniquement) | via le proxy d'entreprise le cas échéant (voir §6) |
| Droits administrateur | **non** | |
| Docker | **non** | |
| Espace disque | ~1,5 Go | venv + dépendances |

Aucune clé API n'est nécessaire : sans clé, le LLM fonctionne en mode
« fallback local » (templates experts) et les données de marché utilisent
Energy-Charts / Open-Meteo (publics) ou le générateur mock si le réseau
sortant est filtré.

---

## 2. Installation : `setup.ps1`

```powershell
.\setup.ps1            # installation standard
.\setup.ps1 -Dev       # + pytest / black / flake8
.\setup.ps1 -Force     # recrée le .venv de zéro
.\setup.ps1 -Python "C:\Users\moi\AppData\Local\Programs\Python\Python311\python.exe"
.\setup.ps1 -Portable  # Python portable dans .\.python\ (rien d'installé sur le poste)
.\setup.ps1 -Offline   # n'essaie jamais de télécharger Python
```

Ce que fait le script :

1. **Détecte Python 3.10-3.12 64 bits** : `py.exe` (Python Launcher), `python.exe`
   du PATH, `%LOCALAPPDATA%\Programs\Python\Python3xx`, Miniconda/Anaconda, scoop,
   `.\.python\` (portable). Les alias du Microsoft Store qui ne pointent vers rien
   sont ignorés.
2. **Crée `.venv\`** à la racine du projet (un seul environnement pour le backend
   et le frontend).
3. **Installe `requirements-windows.txt`** avec `pip install --only-binary :all:` :
   uniquement des wheels précompilées → aucune compilation, aucun compilateur C++.
   Les différences avec `backend/requirements.txt` (utilisé par Docker) sont
   documentées en tête du fichier (python-pptx 0.6.23, suppression de
   psycopg2/sqlalchemy/alembic qui ne sont pas utilisés par le code).
4. **Crée `.env`** (copie de `.env.example`) et les dossiers `backend\generated\`,
   `logs\`.
5. **Vérifie** l'installation (`scripts\windows\check_install.py`) : import du
   backend, du frontend, chemins de la knowledge base et des fichiers générés.

Le script est **idempotent** : relancez-le après un `git pull` pour mettre à
jour les dépendances.

---

## 3. Si Python n'est pas installé

`setup.ps1` vous propose deux options, toutes deux **sans droits admin** :

**Option 1 (recommandée) – installeur officiel en mode « pour moi uniquement »**
Télécharge `python-3.11.x-amd64.exe` depuis python.org et l'exécute avec
`InstallAllUsers=0 PrependPath=1` → installation dans
`%LOCALAPPDATA%\Programs\Python\Python311`, aucune élévation UAC.

**Option 2 – Python portable dans le projet**
Télécharge le paquet officiel de la Python Software Foundation publié sur
nuget.org (même build que python.org, avec pip et venv inclus) et l'extrait dans
`.\.python\`. Rien n'est écrit dans le registre ni dans le PATH. Idéal si
l'exécution d'installeurs `.exe` est bloquée. (Le paquet « embeddable » de
python.org n'est pas utilisé car il n'inclut ni pip ni venv.)

**Installation manuelle** : https://www.python.org/downloads/windows/ →
« Windows installer (64-bit) » → cochez *Add python.exe to PATH*, **décochez**
*Use admin privileges when installing py.exe*, puis relancez `.\setup.ps1`.

Si la DSI met à disposition Python via un portail logiciel (Software Center,
Intune), c'est aussi parfaitement adapté : n'importe quel Python 3.10-3.12
64 bits convient.

---

## 4. Lancement : `start.ps1`

```powershell
.\start.ps1                                  # backend + frontend, ouvre le navigateur
.\start.ps1 -NoBrowser
.\start.ps1 -BackendPort 8010 -FrontendPort 8511
.\start.ps1 -BackendOnly                     # uniquement l'API
.\start.ps1 -FrontendOnly                    # uniquement Streamlit (backend déjà actif)
.\start.ps1 -NoReload                        # backend sans rechargement automatique
.\start.ps1 -Background                      # sans fenêtres, logs dans .\logs\
```

Comportement :

- ouvre **deux fenêtres PowerShell** (« PMIA Backend », « PMIA Frontend ») ; fermer
  une fenêtre arrête le service correspondant ;
- attend que `http://localhost:8000/health` réponde avant de lancer le frontend ;
- lit les ports dans `.env` (`BACKEND_PORT`, `FRONTEND_PORT`) ;
- positionne `BACKEND_URL`, `PYTHONUTF8=1`, `NO_PROXY=localhost,127.0.0.1` (le
  trafic local ne passe jamais par le proxy d'entreprise) ;
- enregistre les PID dans `logs\pids.json` pour `stop.ps1`.

Arrêt : `.\stop.ps1` (termine les processus enregistrés et libère les ports 8000
/ 8501 s'ils sont encore tenus par un Python du projet ; ne touche à aucun autre
programme).

Tests : `.\test.ps1` (installe pytest à la volée si besoin).

---

## 5. Où sont les fichiers ?

| Élément | Emplacement | Variable d'environnement |
|---------|-------------|--------------------------|
| Environnement virtuel | `.\.venv\` | – |
| Python portable (option) | `.\.python\` | – |
| Configuration | `.\.env` | – |
| Présentations générées (PPTX/DOCX/PDF) | `.\backend\generated\` | `GENERATED_DIR` |
| Base de connaissances | `.\knowledge_base\` | `KNOWLEDGE_BASE_DIR` |
| Jeux de données d'exemple | `.\backend\data_samples\` | `DATA_SAMPLES_DIR` |
| Logs (mode `-Background`) | `.\logs\` | – |

Tous ces chemins sont résolus **de façon absolue** par le code
(`backend/app/core/paths.py`, `frontend/utils/paths.py`) : le projet fonctionne
quel que soit le répertoire depuis lequel il est lancé (PowerShell, VS Code,
double-clic sur `start.cmd`).

Les fichiers générés sont téléchargeables depuis la page *Presentation Builder*
(boutons ⬇️) ou via l'API : `GET /api/v1/presentation/files` puis
`GET /api/v1/presentation/download/{nom}`.

---

## 6. Dépannage

### « L'exécution de scripts est désactivée sur ce système »
Politique d'exécution PowerShell restrictive (fréquent en entreprise). Sans admin :

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
# ou, pour la session courante :
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# ou, de façon persistante pour votre utilisateur (si autorisé par la GPO) :
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Les fichiers `setup.cmd` / `start.cmd` / `stop.cmd` appliquent automatiquement
`-ExecutionPolicy Bypass` (double-clic).

Si le dépôt a été téléchargé en ZIP, Windows peut marquer les fichiers comme
« bloqués » : `Get-ChildItem -Recurse | Unblock-File`.

### `python` ouvre le Microsoft Store
C'est l'alias d'exécution d'application de Windows. `setup.ps1` l'ignore
automatiquement. Pour le désactiver : *Paramètres → Applications → Paramètres
avancés des applications → Alias d'exécution d'application* → désactivez
`python.exe` et `python3.exe`.

### pip : `ProxyError`, `SSLError`, `Could not fetch URL`, `CERTIFICATE_VERIFY_FAILED`
Proxy d'entreprise. Dans la session PowerShell **avant** `.\setup.ps1` :

```powershell
$env:HTTPS_PROXY = "http://proxy.entreprise.local:8080"   # éventuellement http://user:mdp@proxy:8080
$env:HTTP_PROXY  = $env:HTTPS_PROXY
```

Si le proxy fait de l'inspection SSL (certificat racine interne), pip rejette le
certificat. Créez `%APPDATA%\pip\pip.ini` :

```ini
[global]
trusted-host = pypi.org
               files.pythonhosted.org
```

ou, plus propre, pointez pip vers le bundle de certificats de l'entreprise :
`$env:PIP_CERT = "C:\chemin\ca-entreprise.pem"` (et
`$env:REQUESTS_CA_BUNDLE = $env:PIP_CERT` pour l'application).

Dépôt PyPI interne (Artifactory / Nexus) :
`$env:PIP_INDEX_URL = "https://artifactory.entreprise.local/artifactory/api/pypi/pypi-remote/simple"`.

### pip : `No matching distribution found` / `Could not find a version that satisfies`
Presque toujours une version de Python non supportée (3.13+, ou 32 bits).
Vérifiez avec `py -0p` ou `python -c "import sys,platform;print(sys.version, platform.architecture())"`
puis : `.\setup.ps1 -Force -Python <chemin vers un python 3.11 64 bits>`.

### « Le port 8000 / 8501 est occupé »
Un ancien lancement tourne encore : `.\stop.ps1`. Sinon, choisissez d'autres
ports : `.\start.ps1 -BackendPort 8010 -FrontendPort 8511` (ou modifiez
`BACKEND_PORT` / `FRONTEND_PORT` dans `.env`).

### Le frontend affiche « Backend KO »
- La fenêtre backend affiche-t-elle une erreur ? Le premier démarrage peut
  prendre 10-20 s (import de pandas, langchain…).
- Vérifiez http://localhost:8000/health dans le navigateur.
- Si un proxy est configuré dans les variables d'environnement, assurez-vous que
  `NO_PROXY` contient `localhost,127.0.0.1` (`start.ps1` le fait automatiquement).

### `/health` indique `"energy_charts": false, "open_meteo": false`
Le poste n'a pas accès à ces APIs publiques (filtrage sortant). Ce n'est pas
bloquant : l'application bascule automatiquement sur le générateur mock. Pour
utiliser les APIs réelles à travers le proxy, définissez `HTTPS_PROXY` avant
`.\start.ps1`.

### Antivirus / EDR bloque `python.exe` du venv
Certaines solutions bloquent les exécutables dans les dossiers utilisateur.
Demandez une exclusion pour le dossier du projet, ou installez le projet dans un
emplacement autorisé par la politique (ex. `C:\Dev\`).

### Chemin avec espaces ou accents
Supporté, mais un chemin court sans caractères spéciaux (`C:\Dev\Agent`) évite
les surprises avec certains outils tiers. Évitez les dossiers synchronisés
OneDrive pour `.venv` (lenteur, verrous de fichiers).

### Windows PowerShell 5.1 : accents mal affichés
Cosmétique. Les scripts forcent l'UTF-8 (`PYTHONUTF8=1`) pour Python ; pour la
console elle-même : `chcp 65001` ou utilisez Windows Terminal / PowerShell 7.

---

## 7. Lancement manuel (sans les scripts)

Pour comprendre ce que font les scripts, ou pour déboguer :

```powershell
# Terminal 1 - backend
cd Agent
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - frontend
cd Agent
.\.venv\Scripts\Activate.ps1
$env:BACKEND_URL = "http://localhost:8000"
cd frontend
python -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

Si `Activate.ps1` est bloqué par la politique d'exécution, utilisez directement
`.\.venv\Scripts\python.exe -m uvicorn ...` sans activer le venv.

---

## 8. VS Code

Ouvrez le dossier `Agent` : l'interpréteur `.venv\Scripts\python.exe` est
présélectionné (`.vscode/settings.json`). Tâches disponibles
(*Terminal → Run Task…*) : `Windows: Setup`, `Windows: Start`, `Windows: Stop`,
`Windows: Tests`. Le débogage `F5` (« Backend FastAPI », « Frontend Streamlit »,
compound) utilise l'interpréteur sélectionné.

---

## 9. Mise à jour

```powershell
git pull
.\setup.ps1      # met à jour les dépendances si requirements-windows.txt a changé
.\start.ps1
```

## 10. Désinstallation

Supprimez le dossier du projet (tout est contenu dedans : `.venv`, `.python`,
`generated`, `logs`). Si vous avez choisi l'option 1 (installeur python.org),
Python se désinstalle depuis *Paramètres → Applications*.
