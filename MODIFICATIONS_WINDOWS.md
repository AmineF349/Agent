# Note explicative — passage du projet en natif Windows (sans Docker)

> **À qui s'adresse ce document** : à toute personne qui reprend le dépôt et
> veut comprendre *ce qui a été changé, pourquoi, et ce qui a été vérifié*.
> Le mode d'emploi utilisateur est dans
> [`docs/INSTALLATION_WINDOWS.md`](docs/INSTALLATION_WINDOWS.md).

| | |
|---|---|
| **Branche** | `arena/01a0a4e1-agent` |
| **PR** | [#2](https://github.com/AmineF349/Agent/pull/2) → base `arena/01a09f1d-agent` |
| **Volume** | liste complète en §8 — le compte exact est sur l'onglet *Files changed* de la PR #2 (tout compteur recopié ici deviendrait faux au prochain commit) |
| **Objectif** | Installer et lancer 100 % du projet sur Windows, **sans Docker Desktop** et **sans droits administrateur** |

### En 30 secondes

- **Le problème** : le seul chemin d'installation fiable était `docker-compose up --build`.
- **La clé** : PostgreSQL est déclaré dans le compose mais **jamais utilisé** par le code,
  il n'y a **pas de Redis**, et tous les services externes ont un repli local.
  → **aucun service externe n'est requis**, donc Docker n'apportait rien d'indispensable.
- **La solution** : `setup.ps1` + `start.ps1`, tout dans le dossier du dépôt,
  écoute en `127.0.0.1`, Python téléchargé en version *sans installation* s'il manque.
- **3 bugs corrigés au passage**, dont un bloquant (`ModuleNotFoundError: No module named 'backend'`
  qui faisait planter la page *Data Analysis* dès l'affichage).
- **Docker n'est pas cassé** : `docker-compose` et `Dockerfile.frontend` gardent
  exactement le même comportement (voir §5).
- **Vérifié** : 18/18 tests, backend démarré avec la commande exacte de `start.ps1`,
  7/7 pages Streamlit, 8/8 clics de bouton.
- **Non vérifié** : les `.ps1` n'ont pas pu être **exécutés** sur Windows
  (PowerShell non installable dans l'environnement de test). Voir §6.

---

## 1. Le problème de départ

Le dépôt ne proposait qu'un seul chemin d'installation fiable :

```bash
cp .env.example .env
docker-compose up --build
```

L'option « locale » du README était écrite pour bash (`source`, `cp`, `lsof`)
et n'était pas testée. Sur un poste Windows dont Docker Desktop est bloqué par
la politique informatique, il n'existait donc **aucun chemin fonctionnel**.

---

## 2. Analyse préalable — ce qui était réellement nécessaire

J'ai cherché ce que Docker apportait d'indispensable. Résultat : **presque rien**.

### 2.1 PostgreSQL : déclaré, jamais utilisé

`docker-compose.yml` déclare un service `postgres:15-alpine` avec healthcheck et
volume. Mais dans `backend/app/` :

- aucun `create_engine`
- aucun import de `psycopg2`
- aucune migration Alembic appliquée au démarrage

`grep -niE "postgres|psycopg|sqlalchemy|DATABASE_URL"` sur tout `backend/app/`
ne remonte **qu'une seule ligne** :

```python
# backend/app/core/config.py
DATABASE_URL: Optional[str] = None
```

La persistance réelle est **fichier** : `backend/app/data/repositories/file_repo.py`
écrit du JSON dans `generated/`. À noter au passage : `FileRepository` n'est
instanciée **nulle part** dans le code actuel (`grep -rn "FileRepository(" backend/`
→ 0 résultat), c'est du code mort.

### 2.2 Redis : absent

Aucune occurrence de `redis` dans tout le dépôt.

### 2.3 Services externes : tous facultatifs

| Service | Clé | Repli si absent |
|---|---|---|
| Energy-Charts.info | aucune | `MOCK_DATA_FALLBACK=true` |
| Open-Meteo | aucune | `MOCK_DATA_FALLBACK=true` |
| ENTSO-E | gratuite, optionnelle | Energy-Charts + mock |
| OpenAI / Claude / Azure | payante, optionnelle | `LLMProvider` → templates experts locaux |

### 2.4 Conclusion

**Aucun service externe n'est requis.** Le seul prérequis réel est un
interpréteur Python. C'est ce qui rend le mode natif possible.

---

## 3. Ce qui a été ajouté

### 3.1 Points d'entrée PowerShell

| Fichier | Rôle |
|---|---|
| `setup.ps1` | Détection/bootstrap Python, `.venv`, dépendances, `.env`, config Streamlit, auto-diagnostic |
| `start.ps1` | Backend uvicorn + frontend Streamlit, attente de `/health`, ouverture du navigateur |
| `stop.ps1` | Arrêt de l'arbre de processus + recherche des orphelins |
| `test.ps1` | `pytest backend/tests` |
| `setup.bat` `start.bat` `stop.bat` `test.bat` | Contournent `ExecutionPolicy Restricted` sans droits admin |

```powershell
.\setup.ps1
.\start.ps1
```

### 3.2 Outils sous-jacents

| Fichier | Rôle |
|---|---|
| `scripts/win/Common.ps1` | Bibliothèque partagée : détection Python, ports, health-check, proxy, retries pip |
| `scripts/win/env_writer.py` | Génère `.env` et neutralise les hôtes Docker — **idempotent** |
| `scripts/win/doctor.py` | Auto-diagnostic, 10 familles de contrôles |
| `frontend/.streamlit/config.toml` | Streamlit en `127.0.0.1`, sans télémétrie |
| `backend/requirements-dev.txt` | `pytest` |
| `.gitattributes` | `eol=crlf` imposé sur `.ps1`/`.bat` |

### 3.3 Garanties « sans droits administrateur »

| Risque | Traitement |
|---|---|
| Python absent | Zip officiel python.org **dézipppé** dans `.python\` : ni installeur, ni registre, ni UAC |
| Repli si le zip échoue | Installeur `.exe` en `InstallAllUsers=0` (aucune élévation) |
| Pare-feu Windows | Écoute en `127.0.0.1` → aucune règle, aucune invite |
| Stratégie d'exécution | Wrappers `.bat` avec `-ExecutionPolicy Bypass` |
| AppLocker / WDAC | Aucun appel .NET dans les scripts → compatible *Constrained Language Mode* |
| Proxy / miroir interne | `-Proxy`, `-IndexUrl`, `HTTPS_PROXY` détecté, 2 retries pip |
| Écritures hors dépôt | Aucune, hormis le cache pip (`%LOCALAPPDATA%\pip\cache`) |

Les versions cibles sont **3.10 – 3.12 en 64 bits** : `numpy==1.26.4` et
`pydantic-core==2.16.3` n'ont pas de wheel pour 3.13, et `numpy`/`polars` ne
sont pas fournis en 32 bits.

---

## 4. Les 3 bugs corrigés (trouvés en lançant réellement l'application)

### 4.1 `ModuleNotFoundError: No module named 'backend'` — **bloquant**

Les pages Streamlit importent directement du code backend pour calculer
localement :

```python
from backend.app.services.market_analysis_engine import MarketAnalysisEngine
```

**16 imports** de ce type dans `frontend/pages/` :

| Fichier | Nb |
|---|---|
| `2_Data_Analysis.py` | 5 |
| `5_Meeting_Assistant.py` | 4 |
| `3_Scenario_Review.py` | 3 |
| `4_Presentation_Builder.py` | 2 |
| `6_Knowledge_Center.py` | 2 |

`backend` est un **paquet d'espace de noms PEP 420** (il n'existe pas de
`backend/__init__.py`) : ces imports ne fonctionnent que si la **racine du
dépôt** est dans `sys.path`.

**Conséquence mesurée** : la page *Data Analysis* plantait dès l'affichage, sur
l'option par défaut « Mock FR 30j ».

**Correction** :

- `frontend/utils/__init__.py` (importé par toutes les pages via
  `from utils.api_client import APIClient`) ajoute la racine du dépôt et
  `frontend/` à `sys.path`, et expose `backend_available()` ;
- `start.ps1` positionne `PYTHONPATH` sur la racine pour le processus frontend ;
- l'import de `2_Data_Analysis.py` est protégé par un `try/except ImportError`
  qui affiche un message explicite au lieu de planter.

> ⚠️ Sous Docker, `Dockerfile.frontend` ne copie que `frontend/` : le paquet
> `backend` y est absent et ces imports ne peuvent pas fonctionner. **Limite
> pré-existante, non modifiée ici.** En natif Windows, backend et frontend
> partagent le même `.venv` : tout fonctionne.

### 4.2 Dossiers parasites créés par le frontend

`backend/app/core/config.py` créait `generated/` et `data_samples/`
**relativement au répertoire courant** :

```python
os.makedirs("generated", exist_ok=True)      # avant
```

Quand le frontend importait le backend, cela créait `frontend/generated/` et
`frontend/data_samples/`. Ancré désormais sur le paquet backend :

```python
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _folder in ("generated", "data_samples"):
    os.makedirs(os.path.join(BACKEND_DIR, _folder), exist_ok=True)
```

Sous Docker, `/app/app/core/config.py` → `/app` : **comportement identique**.

### 4.3 `psycopg2-binary` inutile sous Windows

```
psycopg2-binary==2.9.9; sys_platform != "win32"
```

Binaire PostgreSQL qui ne sert à rien (cf. §2.1). Sous Linux/Docker il reste
installé, donc `docker-compose` est inchangé.

---

## 5. Pourquoi Docker n'est pas cassé

Deux mécanismes de précédence garantissent que l'installation Docker continue
de fonctionner à l'identique :

| Changement | Pourquoi Docker n'est pas impacté |
|---|---|
| `DATABASE_URL=` vide dans `.env.example` | `docker-compose.yml` injecte sa propre valeur via la section `environment:`, qui **a priorité sur `env_file`** |
| `frontend/.streamlit/config.toml` avec `address = "127.0.0.1"` | `Dockerfile.frontend` passe `--server.address=0.0.0.0` en ligne de commande ; **les flags CLI ont priorité sur `config.toml`** |
| `psycopg2-binary` marqué `sys_platform != "win32"` | L'image `python:3.11-slim` est Linux → le paquet est toujours installé |

Les deux précédences ont été **observées en vrai** : au démarrage de Streamlit,
l'URL affichée était `http://0.0.0.0:8501` alors que `config.toml` indique
`127.0.0.1`, et le warning `server.enableCORS` prouvait que `config.toml` était
bien lu.

---

## 6. Ce qui a été vérifié — et comment

| Vérification | Commande / méthode | Résultat |
|---|---|---|
| Suite de tests du projet | `pytest backend/tests -v` | **18 passed** |
| Démarrage backend | **la commande exacte de `start.ps1`**, cwd `backend/` | `/health` → `200 {"status":"ok",...}` |
| Swagger | `GET /docs` | `200` |
| Cœur métier | `POST /api/v1/market-analysis/analyze` | 12 métriques (baseload 63.33, capture rate 1.1468…) |
| Base de connaissances | `POST /api/v1/knowledge/search` | résultats réels depuis `knowledge_base/` |
| Toutes les pages Streamlit | `streamlit.testing.v1.AppTest` | **7/7** scripts sans exception |
| Les chemins qui importent le backend | `AppTest` + `.click()` sur 8 boutons | **8/8** OK (KPI → 12 métriques, BESS, benchmarks, réunion, CR, recherche, listing) |
| Génération du `.env` | `env_writer.py` exécuté | création puis **idempotence** (« aucune modification nécessaire ») |
| Normalisation d'un `.env` Docker | `.env` modifié à la main puis relancé | `@postgres:` → vide, `http://backend:8000` → `http://127.0.0.1:8080` |
| Auto-diagnostic | `doctor.py` exécuté | code retour **0**, **30 routes** FastAPI détectées |
| Scripts PowerShell | contrôle lexical (chaînes, here-strings, blocs) | 5/5 équilibrés |

### ⚠️ Ce qui n'a PAS pu être vérifié

**Les `.ps1` n'ont jamais été exécutés sur Windows.** PowerShell n'est pas
installable dans l'environnement de vérification : les assets des releases
GitHub (`release-assets.githubusercontent.com`) y sont injoignables, tout comme
`packages.microsoft.com`.

Les scripts ont donc été écrits prudemment — Windows PowerShell 5.1 compatible
(pas de `??`, pas de `?:`, pas de `&&`, pas de `ForEach-Object -Parallel`),
aucun appel .NET statique (compatible *Constrained Language Mode*), fichiers en
UTF-8 **avec BOM** et fins de ligne **CRLF** — puis validés lexicalement.

**Un premier `.\setup.ps1` sur un vrai poste Windows reste à faire.** C'est le
seul point non couvert.

Deuxième point non vérifiable ici : le téléchargement de Python depuis
python.org (le domaine est bloqué dans la sandbox). L'URL et le SHA-256 ont été
vérifiés dans le fichier officiel
`https://www.python.org/ftp/python/3.11.9/windows-3.11.9.json` :

| Fichier | SHA-256 |
|---|---|
| `python-3.11.9-amd64.zip` | `4ba90a4ab8990891033d37ff04d2047fdae8948d0d2729a68d3a6a17c585b681` |
| `python-3.11.9-arm64.zip` | `bf349dcc73119f82a4fde5ce579d7edf7f4b7ea83ee98c174320e5ef184111d4` |

---

## 7. État du dépôt git

```
* (commits de cette session, sur arena/01a0a4e1-agent)
* e3863e6  feat: Power Market Intelligence Agent v1.0.0         <- intact
* 2b74842  Initial commit                                       <- intact
```

Vérifié par `git ls-remote --heads origin` :

| Branche | SHA | État |
|---|---|---|
| `main` | `2b74842` | **inchangée** |
| `arena/01a09f1d-agent` | `e3863e6` | **inchangée** |
| `arena/01a0a06d-agent` | `addafa83` | jamais touchée |
| `arena/01a0a4e1-agent` | tip de la PR #2 | seule branche modifiée |

- Historique **linéaire**, aucun rebase, aucun force-push, aucun commit de merge
  (la reprise de `arena/01a09f1d-agent` était un *fast-forward* :
  `git log --merges` est vide).
- Les commits de cette session portent l'auteur `Arena Agent <agent@arena.ai>`,
  passé en ligne de commande (`git -c user.name=... commit`) : **rien n'a été
  écrit dans `.git/config`**.

**La PR #2 n'est pas encore fusionnée** : `arena/01a09f1d-agent` ne contient pas
encore ces modifications. Fusion en un clic sur la PR, ou :

```bash
gh pr merge 2 --repo AmineF349/Agent --merge
```

---

## 8. Fichiers livrés

### Créés (17)

```
setup.ps1                            installation (Python, .venv, deps, .env, diagnostic)
start.ps1                            demarrage backend + frontend
stop.ps1                             arret de l'arbre de processus
test.ps1                             pytest
setup.bat                            wrapper anti-ExecutionPolicy
start.bat                            wrapper anti-ExecutionPolicy
stop.bat                             wrapper anti-ExecutionPolicy
test.bat                             wrapper anti-ExecutionPolicy
scripts/win/Common.ps1               bibliotheque partagee
scripts/win/env_writer.py            generation du .env natif
scripts/win/doctor.py                auto-diagnostic
frontend/.streamlit/config.toml      Streamlit local, sans telemetrie
backend/requirements-dev.txt         pytest
docs/INSTALLATION_WINDOWS.md         mode d'emploi utilisateur
MODIFICATIONS_WINDOWS.md             ce document
.gitattributes                       CRLF impose sur les scripts Windows
LICENSE                              manquait depuis e3863e6 (lien casse)
```

### Modifiés (12)

```
.env.example                        DATABASE_URL videe, BACKEND_HOST/BACKEND_URL ajoutes
.gitignore                          *.pid, .python/, tools/, secrets.toml
README.md                           Quick Start Windows natif en tete
docs/INSTALLATION.md                Option 0 Windows + corrections bash-only
backend/app/core/config.py          generated/ et data_samples/ ancres sur le paquet
backend/requirements.txt            psycopg2-binary -> sys_platform != "win32"
frontend/utils/__init__.py          racine du depot ajoutee a sys.path
frontend/pages/2_Data_Analysis.py   ImportError degrade en message explicite
frontend/components/sidebar.py      affiche la vraie URL backend
.vscode/settings.json               interpreteur auto-detecte (plus de chemin Linux fige)
.vscode/tasks.json                  3 taches Windows + commandes venv-relative
.vscode/launch.json                 0.0.0.0 -> 127.0.0.1
```

---

## 9. Pour aller plus loin

- **Mode d'emploi** : [`docs/INSTALLATION_WINDOWS.md`](docs/INSTALLATION_WINDOWS.md)
  (GPO, proxy, miroir PyPI, dépannage, désinstallation)
- **Vue produit** : [`README.md`](README.md)
- **Architecture** : [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **API** : [`docs/API_DOCS.md`](docs/API_DOCS.md)

### Piste d'amélioration non traitée

Les 16 imports `from backend.app...` dans le frontend contournent l'API HTTP et
créent un couplage fort entre les deux processus. En natif Windows cela
fonctionne (même `.venv`), mais la cible architecturale décrite dans
`ARCHITECTURE.md` est `Frontend --HTTP--> Backend`. Remplacer ces imports par
des appels `APIClient` supprimerait le couplage **et** réparerait le mode
Docker. Non fait ici : cela toucherait 5 pages et sortait du périmètre
« rendre le projet lançable sur Windows ».
