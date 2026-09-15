# Installation Windows sans Docker (entreprise restreinte)

Ce guide installe **Power Market Intelligence Agent** en natif sur un poste
Windows 10 / 11, **sans Docker Desktop**, **sans WSL** et **sans droits
administrateur**.

> Objectif : contourner le blocage de Docker par la politique informatique, en
> n'utilisant que ce qu'un utilisateur standard a le droit de faire : écrire
> dans son propre dossier, créer un environnement virtuel Python, écouter sur
> `127.0.0.1`.
>
> 📄 **Liste détaillée des modifications apportées au dépôt, avec les preuves de
> vérification : [`../MODIFICATIONS_WINDOWS.md`](../MODIFICATIONS_WINDOWS.md)**

---

## 1. Démarrage en 2 commandes

Ouvrez **PowerShell** (pas « PowerShell (admin) »), placez-vous dans le dossier
du dépôt, puis :

```powershell
.\setup.ps1
.\start.ps1
```

Puis ouvrez :

| Service | URL |
|---|---|
| Interface Streamlit | <http://127.0.0.1:8501> |
| API + Swagger | <http://127.0.0.1:8000/docs> |
| Sonde de santé | <http://127.0.0.1:8000/health> |

Pour tout arrêter :

```powershell
.\stop.ps1
```

### Si PowerShell refuse d'exécuter le script

Beaucoup de parcs d'entreprise sont en `ExecutionPolicy = Restricted`. Vous
verrez :

```
Le fichier ...\setup.ps1 ne peut pas être chargé car l'exécution de scripts
est désactivée sur ce système.
```

Deux solutions, aucune ne demande les droits admin :

```powershell
# Solution A : lancer via le wrapper .bat (bypass limité à ce processus)
.\setup.bat
.\start.bat

# Solution B : bypass explicite
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Vous pouvez aussi n'autoriser que votre propre compte, sans admin :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 2. Ce que fait `setup.ps1`

| Étape | Action | Droits requis |
|---|---|---|
| 1 | Détecte un Python **3.10 – 3.12 en 64 bits**. S'il est absent, télécharge la distribution officielle python.org *sans installation* (`python-3.11.9-amd64.zip`) et la dézippe dans `.python\` | aucun |
| 2 | Crée l'environnement virtuel `.venv\` | aucun |
| 3 | `pip install -r backend\requirements.txt` puis `-r frontend\requirements.txt` | aucun |
| 4 | Génère `.env` depuis `.env.example` en neutralisant ce qui dépend de Docker | aucun |
| 5 | Génère `frontend\.streamlit\config.toml` et les dossiers de sortie | aucun |
| 6 | Lance l'auto-diagnostic `scripts\win\doctor.py` (10 familles de contrôles) | aucun |

Rien n'est écrit hors du dossier du dépôt, hormis le cache pip
(`%LOCALAPPDATA%\pip\cache`). Aucune clé de registre, aucun service Windows,
aucune règle de pare-feu.

### Options de `setup.ps1`

```powershell
.\setup.ps1 -Proxy "http://proxy.entreprise.com:8080"     # proxy HTTP(S)
.\setup.ps1 -IndexUrl "https://pypi.entreprise.com/simple" # miroir PyPI interne
.\setup.ps1 -WithDev                                       # + pytest (backend\requirements-dev.txt)
.\setup.ps1 -Recreate                                      # recrée .venv et .env de zéro
.\setup.ps1 -BackendPort 8080 -FrontendPort 8600           # ports non standards
.\setup.ps1 -SkipDeps                                      # configuration seule
.\setup.ps1 -NoDownload                                    # interdit tout téléchargement de Python
```

Les variables d'environnement `HTTPS_PROXY` / `HTTP_PROXY` sont détectées
automatiquement si `-Proxy` n'est pas fourni.

---

## 3. Pourquoi aucun service externe n'est nécessaire

Analyse du dépôt : le `docker-compose.yml` déclare un service **PostgreSQL 15**,
mais **aucun module du backend n'ouvre de connexion SQL** — il n'y a ni
`create_engine`, ni import de `psycopg2`, ni migration Alembic appliquée au
démarrage. La persistance réelle est **fichier**, via
`backend/app/data/repositories/file_repo.py` qui écrit du JSON dans
`backend\generated\`.

Il n'y a **aucun Redis** dans le projet.

Conséquences appliquées par cette installation native :

- `DATABASE_URL` est laissée **vide** dans `.env` (l'hôte `postgres` du
  `docker-compose.yml` n'existe que dans le réseau Docker) ;
- `psycopg2-binary` n'est plus installé sous Windows
  (`psycopg2-binary==2.9.9; sys_platform != "win32"`) : binaire inutile ;
- le comportement Docker est **inchangé** : `docker-compose.yml` injecte
  `DATABASE_URL` via sa section `environment:`, qui a priorité sur `env_file`.

Les seules sorties réseau sont les **API publiques gratuites** (Energy-Charts,
Open-Meteo) et, si vous renseignez une clé, un fournisseur LLM. Tout est
optionnel : `MOCK_DATA_FALLBACK=true` fournit des données réalistes de repli et
`LLMProvider` retombe sur des templates experts locaux. **L'application est
100 % fonctionnelle hors ligne.**

---

## 3 bis. Corrections de code nécessaires au mode natif

Trois défauts du dépôt bloquaient un lancement complet hors Docker. Ils sont
corrigés, et le comportement Docker reste identique.

### a) `ModuleNotFoundError: No module named 'backend'` (bloquant)

Les pages Streamlit importent directement du code backend pour calculer
localement :

```python
from backend.app.services.market_analysis_engine import MarketAnalysisEngine
```

16 imports de ce type existent dans `frontend/pages/` (5 dans Data Analysis, 4 dans
Meeting Assistant, 3 dans Scenario Review, 2 dans Presentation Builder, 2 dans
Knowledge Center). `backend` est un paquet
d'espace de noms PEP 420 (il n'y a pas de `backend/__init__.py`) : ces imports
ne fonctionnent **que si la racine du dépôt est dans `sys.path`**.

Résultat avant correction : la page **Data Analysis** plantait dès l'affichage,
sur l'option par défaut « Mock FR 30j ».

Correction : `frontend/utils/__init__.py` — importé par toutes les pages via
`from utils.api_client import APIClient` — ajoute désormais la racine du dépôt
et le dossier `frontend/` à `sys.path`, et expose `backend_available()`.
En complément, `start.ps1` positionne `PYTHONPATH` sur la racine du dépôt pour
le processus frontend, et l'import de `2_Data_Analysis.py` est protégé par un
`try/except ImportError` qui affiche un message explicite au lieu de planter.

> ⚠️ Sous Docker, l'image `Dockerfile.frontend` ne contient que `frontend/` :
> le paquet `backend` y est absent et ces imports ne peuvent pas fonctionner
> (limite **pré-existante**, non modifiée ici). En natif Windows, backend et
> frontend partagent le même `.venv` : tout fonctionne.

### b) Dossiers parasites créés par le frontend

`backend/app/core/config.py` créait `generated/` et `data_samples/`
**relativement au répertoire courant**. Quand le frontend importait le backend,
cela créait `frontend/generated/` et `frontend/data_samples/`.

Correction : ces dossiers sont ancrés sur le dossier du paquet backend.
Sous Docker (`/app/app/core/config.py`) le résultat reste `/app`, donc
inchangé.

### c) `psycopg2-binary` inutile sous Windows

Voir §3 : le marqueur `sys_platform != "win32"` évite d'installer un binaire
PostgreSQL qui ne sert à rien. Sous Linux/Docker, il est toujours installé.

---

## 4. Ports et pare-feu

| Rôle | Port | Adresse d'écoute par défaut |
|---|---|---|
| Backend FastAPI (uvicorn) | 8000 | `127.0.0.1` |
| Frontend Streamlit | 8501 | `127.0.0.1` |

`127.0.0.1` ne déclenche **aucune invite du pare-feu Windows** et ne nécessite
aucune règle, ce qui évite toute demande d'élévation.

Pour exposer l'application sur le réseau (une règle de pare-feu sera alors
demandée) :

```powershell
.\start.ps1 -ListenHost 0.0.0.0
```

Pour changer de port (par exemple si 8000 est pris par un autre logiciel) :

```powershell
.\start.ps1 -BackendPort 8080 -FrontendPort 8600
```

`start.ps1` recalcule alors automatiquement `BACKEND_URL` pour le frontend.

---

## 5. Autres scripts

| Script | Rôle |
|---|---|
| `.\start.ps1` | Démarre backend + frontend dans 2 fenêtres dédiées, attend `/health`, ouvre le navigateur |
| `.\start.ps1 -NoNewWindow` | Tout dans la console courante (backend en arrière-plan) |
| `.\start.ps1 -Reload` | Rechargement à chaud du backend (développement) |
| `.\start.ps1 -NoBrowser` | N'ouvre pas le navigateur |
| `.\stop.ps1` | Arrête l'arbre de processus (PID mémorisés dans `logs\*.pid`) + orphelins |
| `.\test.ps1` | `pytest backend\tests` (18 tests) |
| `.\test.ps1 -InstallDeps` | Installe `pytest` puis lance les tests |

Les `.bat` équivalents (`setup.bat`, `start.bat`, `stop.bat`, `test.bat`)
contournent la stratégie d'exécution PowerShell.

Logs : `logs\backend.log` et `logs\frontend.log` (copie de la sortie des deux
fenêtres via `Tee-Object`).

---

## 6. Auto-diagnostic seul

À tout moment, pour savoir ce qui cloche :

```powershell
.\.venv\Scripts\python.exe scripts\win\doctor.py --root . --backend-port 8000 --frontend-port 8501
```

Contrôles effectués :

1. Python 3.10 – 3.12, 64 bits
2. `.env` présent, `DATABASE_URL` / `BACKEND_URL` non liés à Docker
3. 21 dépendances backend obligatoires importables
4. 9 dépendances optionnelles (avertissement seulement)
5. 6 dépendances frontend importables
6. **`import app.main`** — la preuve que le backend démarre réellement
7. `knowledge_base\` et `backend\data_samples\` accessibles
8. Ports libres
9. `frontend\.streamlit\config.toml` présent
10. Écriture possible dans `backend\generated\` et `logs\`

Code de retour : `0` = OK, `1` = au moins une erreur bloquante.

---

## 7. Dépannage

**« L'exécution de scripts est désactivée »**
→ `.\setup.bat` / `.\start.bat`, ou `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Python introuvable et téléchargement impossible**
→ Faites installer Python 3.11 par votre support (ou téléchargez
`python-3.11.9-amd64.exe` depuis <https://www.python.org/downloads/windows/>),
cochez *Install for me only* — aucune élévation n'est nécessaire — puis
relancez `.\setup.ps1`. Vous pouvez aussi forcer un interprète précis :

```powershell
$env:PMI_PYTHON = "C:\Chemin\vers\python.exe"
.\setup.ps1
```

**`pip` échoue (proxy / TLS / antivirus)**
→ `.\setup.ps1 -Proxy "http://proxy:port"` et/ou
`.\setup.ps1 -IndexUrl "https://pypi.entreprise.com/simple"`.
Le script réessaie 2 fois automatiquement ; le cache pip permet de reprendre.

**Le port 8000 ou 8501 est déjà occupé**
→ `.\start.ps1 -BackendPort 8080 -FrontendPort 8600`.

**Le backend ne répond pas**
→ Regardez la fenêtre *PMI Backend* ou `logs\backend.log`.
Cause n°1 : `.venv` incomplet → `.\setup.ps1 -Recreate`.

**`ModuleNotFoundError: No module named 'app'`**
→ Le backend doit être lancé avec `backend\` comme répertoire de travail :
c'est ce que fait `start.ps1` (`PYTHONPATH` est positionné automatiquement).

**Le frontend affiche « Backend: ... error »**
→ Vérifiez <http://127.0.0.1:8000/health> puis la valeur de `BACKEND_URL`
dans `.env`. `start.ps1` la force à l'URL réelle du backend démarré.

**Windows Defender / antivirus supprime `.venv`**
→ Ajoutez le dossier du dépôt aux exclusions, ou déplacez le dépôt hors d'un
dossier synchronisé (OneDrive, profil itinérant).

**Le dépôt est sur OneDrive et les chemins sont très longs**
→ Clonez plutôt dans `C:\Dev\Agent`. Au-delà de 260 caractères, certaines
installations pip échouent.

**Les pages de données sont vides**
→ Normal sans accès aux APIs publiques ; `MOCK_DATA_FALLBACK=true` doit rester
activé dans `.env`.

---

## 8. Activer les options payantes / externes (facultatif)

Éditez `.env` à la racine du dépôt, puis relancez `.\start.ps1` :

```ini
OPENAI_API_KEY=sk-...
# ou
ANTHROPIC_API_KEY=sk-ant-...
# ou
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<ressource>.openai.azure.com/

ENTSOE_API_KEY=<token gratuit>
```

Sans ces clés, l'application reste entièrement fonctionnelle (LLM local +
Energy-Charts + Open-Meteo + mock).

---

## 9. Désinstallation

Tout est local au dépôt :

```powershell
.\stop.ps1
Remove-Item .venv, .python, tools, logs -Recurse -Force
```

---

## 10. Récapitulatif des fichiers ajoutés pour le mode natif

```
setup.ps1 / start.ps1 / stop.ps1 / test.ps1     points d'entrée PowerShell
setup.bat / start.bat / stop.bat / test.bat     wrappers anti-ExecutionPolicy
scripts/win/Common.ps1                          bibliothèque partagée
scripts/win/env_writer.py                       génération du .env natif
scripts/win/doctor.py                           auto-diagnostic
frontend/.streamlit/config.toml                 Streamlit en 127.0.0.1, sans télémétrie
backend/requirements-dev.txt                    pytest
logs/                                           logs + PID (non versionné)
.venv/  .python/  tools/                        runtime (non versionné)
```

Aucun de ces fichiers ne modifie le comportement de `docker-compose.yml` :
l'installation Docker continue de fonctionner à l'identique.
