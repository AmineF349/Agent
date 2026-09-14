<#
.SYNOPSIS
    Lance le Power Market Intelligence Agent (backend FastAPI + frontend Streamlit)
    sous Windows, sans Docker ni droits administrateur.

.DESCRIPTION
    - Demarre le backend (uvicorn) et le frontend (streamlit) dans deux fenetres
      PowerShell separees, ou en arriere-plan avec -Background (logs dans .\logs\).
    - Attend que le backend reponde sur /health, puis ouvre le navigateur.
    - Les ports sont lus dans .env (BACKEND_PORT / FRONTEND_PORT) ou passes en parametres.
    - Les services ecoutent uniquement sur 127.0.0.1 (aucune exposition reseau,
      aucune regle de pare-feu / droit admin requis).

.PARAMETER BackendPort
    Port du backend FastAPI (defaut : BACKEND_PORT du .env, sinon 8000).

.PARAMETER FrontendPort
    Port du frontend Streamlit (defaut : FRONTEND_PORT du .env, sinon 8501).

.PARAMETER BackendOnly
    Ne lance que le backend.

.PARAMETER FrontendOnly
    Ne lance que le frontend (suppose un backend deja actif).

.PARAMETER NoBrowser
    N'ouvre pas le navigateur automatiquement.

.PARAMETER NoReload
    Desactive le rechargement automatique du backend a chaque modification du code.

.PARAMETER Background
    Lance les services en arriere-plan (sans fenetres), sortie dans .\logs\.
    Arret avec .\stop.ps1.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -BackendPort 8010 -FrontendPort 8511
    .\start.ps1 -Background ; .\stop.ps1
#>
[CmdletBinding()]
param(
    [int] $BackendPort = 0,
    [int] $FrontendPort = 0,
    [switch] $BackendOnly,
    [switch] $FrontendOnly,
    [switch] $NoBrowser,
    [switch] $NoReload,
    [switch] $Background
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root
. (Join-Path $Root "scripts\windows\common.ps1")

Write-Banner "Power Market Intelligence Agent - Demarrage (Windows, sans Docker)"

# --- Environnement virtuel --------------------------------------------------
$VenvPython = Get-VenvPython $Root
if (-not $VenvPython) {
    Write-Fail "Environnement virtuel introuvable (.venv). Lancez d'abord :  .\setup.ps1"
    exit 1
}
if (-not (Test-PythonModule $VenvPython "uvicorn") -or -not (Test-PythonModule $VenvPython "streamlit")) {
    Write-Fail "Dependances manquantes dans .venv. Relancez :  .\setup.ps1"
    exit 1
}

# --- Configuration ----------------------------------------------------------
$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root ".env.example") $EnvFile
    Write-Info ".env cree a partir de .env.example"
}
$dotenv = Read-DotEnv $EnvFile
if ($BackendPort -le 0)  { $BackendPort  = Get-DotEnvInt $dotenv "BACKEND_PORT" 8000 }
if ($FrontendPort -le 0) { $FrontendPort = Get-DotEnvInt $dotenv "FRONTEND_PORT" 8501 }

$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogDir      = Join-Path $Root "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$PidFile = Join-Path $LogDir "pids.json"

$BackendUrl  = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://localhost:$FrontendPort"

$startBackend  = -not $FrontendOnly
$startFrontend = -not $BackendOnly

# --- Verification des ports -------------------------------------------------
if ($startBackend -and (Test-PortInUse $BackendPort)) {
    if (Test-HttpUp "$BackendUrl/health") {
        Write-Warn "Un backend repond deja sur le port $BackendPort : il sera reutilise (.\stop.ps1 pour l'arreter)."
        $startBackend = $false
    } else {
        Write-Fail "Le port $BackendPort est occupe par un autre programme. Utilisez -BackendPort <autre> ou .\stop.ps1"
        exit 1
    }
}
if ($startFrontend -and (Test-PortInUse $FrontendPort)) {
    if (Test-HttpUp "http://127.0.0.1:$FrontendPort/_stcore/health") {
        Write-Warn "Un frontend repond deja sur le port $FrontendPort : il sera reutilise."
        $startFrontend = $false
    } else {
        Write-Fail "Le port $FrontendPort est occupe. Utilisez -FrontendPort <autre> ou .\stop.ps1"
        exit 1
    }
}

# --- Variables d'environnement transmises aux services ---------------------
# (le backend charge lui-meme le .env de la racine ; ici : uniquement le lancement local)
$env:PYTHONUTF8 = "1"                        # UTF-8 partout (accents / emojis dans les logs)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$env:BACKEND_URL = $BackendUrl               # utilise par le frontend (utils/api_client.py)
$env:BACKEND_PORT = "$BackendPort"
$env:FRONTEND_PORT = "$FrontendPort"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_SERVER_HEADLESS = "true"
# Le trafic vers localhost ne doit jamais transiter par le proxy d'entreprise
$noProxy = "localhost,127.0.0.1"
$env:NO_PROXY = if ($env:NO_PROXY) { "$($env:NO_PROXY),$noProxy" } else { $noProxy }
$env:no_proxy = $env:NO_PROXY

$qPython = ConvertTo-PSQuoted $VenvPython
$RunLogged = Join-Path $Root "scripts\windows\run_logged.py"

# Arguments Python de chaque service (tableaux : aucun probleme de quoting)
$backendArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort")
if (-not $NoReload) { $backendArgs += "--reload" }
$frontendArgs = @("-m", "streamlit", "run", "app.py", "--server.port", "$FrontendPort", "--server.address", "127.0.0.1", "--server.headless", "true", "--browser.gatherUsageStats", "false")

$pids = @{}

function Start-ServiceProcess([string] $Title, [string] $WorkDir, [string[]] $PyArgs, [string] $LogName) {
    if ($Background) {
        # Mode arriere-plan : python.exe (sans fenetre) via run_logged.py qui fusionne
        # stdout+stderr dans logs\<service>.log. Pas de fenetre PowerShell intermediaire.
        $logFile = Join-Path $LogDir "$LogName.log"
        $p = Start-Process -FilePath $VenvPython `
            -ArgumentList (ConvertTo-ArgvLine (@($RunLogged, $logFile) + $PyArgs)) `
            -WorkingDirectory $WorkDir -WindowStyle Hidden -PassThru
        Write-Ok "$Title demarre en arriere-plan (PID $($p.Id)) - log : $logFile"
    } else {
        # Mode fenetre : une console PowerShell par service (logs visibles, Ctrl+C pour arreter).
        $qTitle = ConvertTo-PSQuoted $Title
        $qWorkDir = ConvertTo-PSQuoted $WorkDir
        $quotedArgs = ($PyArgs | ForEach-Object { ConvertTo-PSQuoted $_ }) -join " "
        $inner = "`$Host.UI.RawUI.WindowTitle = $qTitle; Set-Location -LiteralPath $qWorkDir; Write-Host $qTitle -ForegroundColor Cyan; Write-Host 'Fermez cette fenetre (ou Ctrl+C) pour arreter ce service.' -ForegroundColor DarkGray; & $qPython $quotedArgs"
        # -Command recoit la commande complete comme UN SEUL argument (quote argv) :
        # aucun probleme avec les espaces des chemins, pas de -EncodedCommand (souvent
        # signale comme suspect par les EDR d'entreprise).
        $p = Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", (ConvertTo-ArgvQuoted $inner)) `
            -WorkingDirectory $WorkDir -PassThru
        Write-Ok "$Title demarre dans une nouvelle fenetre (PID $($p.Id))"
    }
    return $p.Id
}

# --- Backend ----------------------------------------------------------------
if ($startBackend) {
    Write-Step "1/2" "Backend FastAPI  ->  $BackendUrl"
    $pids["backend"] = Start-ServiceProcess "PMIA Backend (FastAPI :$BackendPort)" $BackendDir $backendArgs "backend"

    Write-Info "Attente du backend ($BackendUrl/health)..."
    if (Wait-HttpReady "$BackendUrl/health" 90) {
        Write-Ok "Backend pret : $BackendUrl/docs"
    } else {
        Write-Warn "Le backend ne repond pas encore (premier demarrage lent ?). Consultez la fenetre / les logs backend."
    }
} else {
    Write-Step "1/2" "Backend : non demarre (deja actif ou -FrontendOnly)"
}

# --- Frontend ---------------------------------------------------------------
if ($startFrontend) {
    Write-Step "2/2" "Frontend Streamlit  ->  $FrontendUrl"
    $pids["frontend"] = Start-ServiceProcess "PMIA Frontend (Streamlit :$FrontendPort)" $FrontendDir $frontendArgs "frontend"

    Write-Info "Attente du frontend..."
    if (Wait-HttpReady "http://127.0.0.1:$FrontendPort/_stcore/health" 90) {
        Write-Ok "Frontend pret : $FrontendUrl"
    } else {
        Write-Warn "Le frontend ne repond pas encore. Consultez la fenetre / les logs frontend."
    }
} else {
    Write-Step "2/2" "Frontend : non demarre (deja actif ou -BackendOnly)"
}

# --- Enregistrement des PIDs (pour stop.ps1) --------------------------------
$state = @{}
if (Test-Path $PidFile) {
    try {
        $json = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($prop in $json.PSObject.Properties) { $state[$prop.Name] = $prop.Value }
    } catch { }
}
foreach ($k in $pids.Keys) { $state[$k] = $pids[$k] }
$state["backend_port"] = $BackendPort
$state["frontend_port"] = $FrontendPort
($state | ConvertTo-Json) | Set-Content -Path $PidFile -Encoding UTF8

# --- Resume -----------------------------------------------------------------
Write-Host ""
Write-Banner "Application demarree"
Write-Host "  Frontend (Streamlit) :  $FrontendUrl" -ForegroundColor Cyan
Write-Host "  API Swagger          :  http://localhost:$BackendPort/docs"
Write-Host "  Health               :  http://localhost:$BackendPort/health"
Write-Host ""
if ($Background) {
    Write-Host "  Logs   :  $LogDir\backend.log  |  $LogDir\frontend.log"
    Write-Host "  Arret  :  .\stop.ps1"
} else {
    Write-Host "  Arret  :  fermez les deux fenetres PowerShell, ou lancez .\stop.ps1"
}
Write-Host ""

if (-not $NoBrowser -and -not $BackendOnly) {
    try { Start-Process $FrontendUrl } catch { Write-Info "Ouvrez manuellement : $FrontendUrl" }
}
