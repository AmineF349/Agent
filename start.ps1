<#
.SYNOPSIS
    Demarre Power Market Intelligence Agent en natif Windows (sans Docker).

.DESCRIPTION
    Lance dans deux fenetres console separees :
      * le backend  FastAPI  (uvicorn)   -> http://127.0.0.1:8000/docs
      * le frontend Streamlit            -> http://127.0.0.1:8501

    Les logs sont egalement copies dans logs\backend.log et logs\frontend.log.
    Les PID sont memorises dans logs\*.pid pour que .\stop.ps1 puisse tout
    arreter proprement.

    Ecoute par defaut sur 127.0.0.1 : aucune regle de pare-feu Windows n'est
    necessaire, donc aucune invite d'elevation.

.EXAMPLE
    .\start.ps1

.EXAMPLE
    .\start.ps1 -BackendPort 8080 -FrontendPort 8600

.EXAMPLE
    .\start.ps1 -ListenHost 0.0.0.0      # acces depuis le reseau (ouvre le pare-feu)

.EXAMPLE
    .\start.ps1 -NoNewWindow             # tout dans la console courante
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    # 0 = lire la valeur de .env, sinon port par defaut
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [string]$ListenHost = '127.0.0.1',
    [int]$HealthTimeout = 180,
    [switch]$NoBrowser,
    [switch]$Reload,
    [switch]$NoNewWindow,
    [switch]$SkipHealth
)

. (Join-Path $PSScriptRoot 'scripts\win\Common.ps1')

function ConvertTo-SingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

$root = Get-RepoRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$logDir = Get-LogDir
$backendLog = Join-Path $logDir 'backend.log'
$frontendLog = Join-Path $logDir 'frontend.log'

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host '  Power Market Intelligence Agent - demarrage natif Windows' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan

# --- Pre-requis : environnement virtuel --------------------------------------
$venvPython = Get-VenvPython
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-FailMsg "Environnement virtuel introuvable : $venvPython"
    Write-Host '    Lancez d''abord :  .\setup.ps1' -ForegroundColor Yellow
    exit 1
}

# --- Configuration -----------------------------------------------------------
$envFile = Join-Path $root '.env'
$envValues = Read-EnvFile -Path $envFile
if ($BackendPort -eq 0) {
    if ($envValues.ContainsKey('BACKEND_PORT') -and $envValues['BACKEND_PORT'] -match '^\d+$') { $BackendPort = [int]$envValues['BACKEND_PORT'] }
    else { $BackendPort = 8000 }
}
if ($FrontendPort -eq 0) {
    if ($envValues.ContainsKey('FRONTEND_PORT') -and $envValues['FRONTEND_PORT'] -match '^\d+$') { $FrontendPort = [int]$envValues['FRONTEND_PORT'] }
    else { $FrontendPort = 8501 }
}

$clientHost = $ListenHost
if ($ListenHost -eq '0.0.0.0' -or $ListenHost -eq '::') { $clientHost = '127.0.0.1' }
$backendUrl = "http://${clientHost}:${BackendPort}"

# .env -> environnement du processus (herite par le backend et le frontend).
# Indispensable : pydantic-settings cherche ".env" depuis le cwd (backend\).
if (Test-Path -LiteralPath $envFile) {
    $applied = Import-EnvFile -Path $envFile
    Write-Ok ".env charge ($($applied.Count) variables)."
}
else {
    Write-WarnMsg '.env absent (lancement avec les valeurs par defaut). Executez .\setup.ps1'
}

# Ces deux valeurs doivent imperativement coller aux ports reellement utilises.
Set-Item -Path 'Env:BACKEND_URL' -Value $backendUrl
Set-Item -Path 'Env:BACKEND_PORT' -Value "$BackendPort"
Set-Item -Path 'Env:FRONTEND_PORT' -Value "$FrontendPort"
Set-Item -Path 'Env:PYTHONUNBUFFERED' -Value '1'

# --- Ports -------------------------------------------------------------------
foreach ($p in @(@{ n = 'Backend'; v = $BackendPort }, @{ n = 'Frontend'; v = $FrontendPort })) {
    if (Test-PortInUse -Port $p.v) {
        Write-FailMsg "Le port $($p.v) ($($p.n)) est deja occupe."
        Write-Host '    Si une instance tourne deja :  .\stop.ps1' -ForegroundColor Yellow
        Write-Host "    Sinon changez de port :        .\start.ps1 -$($p.n)Port <port>" -ForegroundColor Yellow
        exit 1
    }
}
Write-Ok "Ports libres : backend $BackendPort, frontend $FrontendPort."

# --- Commandes ----------------------------------------------------------------
$reloadFlag = ''
if ($Reload) { $reloadFlag = ' --reload' }

$backendArgs = @('-m', 'uvicorn', 'app.main:app', '--host', $ListenHost, '--port', "$BackendPort")
if ($Reload) { $backendArgs += '--reload' }
$frontendArgs = @(
    '-m', 'streamlit', 'run', 'app.py',
    '--server.port', "$FrontendPort",
    '--server.address', $ListenHost,
    '--server.headless', 'true',
    '--browser.gatherUsageStats', 'false'
)

# =============================================================================
if ($NoNewWindow) {
    # --- Mode console unique : backend en arriere-plan, frontend au premier plan
    Write-Step "Backend FastAPI sur $backendUrl (log : $backendLog)"
    $env:PYTHONPATH = $backendDir
    $backendProc = Start-Process -FilePath $venvPython -ArgumentList $backendArgs `
        -WorkingDirectory $backendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError (Join-Path $logDir 'backend.err.log')
    Set-Content -LiteralPath (Join-Path $logDir 'backend.pid') -Value $backendProc.Id
    Write-Ok "Backend demarre (PID $($backendProc.Id))."

    if (-not $SkipHealth) {
        Write-Info "Attente de $backendUrl/health ..."
        if (-not (Wait-ForHttp -Url "$backendUrl/health" -TimeoutSeconds $HealthTimeout)) {
            Write-FailMsg "Le backend n'a pas repondu dans les $HealthTimeout s."
            if (Test-Path -LiteralPath $backendLog) { Write-Host (Get-Content -LiteralPath $backendLog -Tail 30 | Out-String) -ForegroundColor Yellow }
            Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
            exit 1
        }
        Write-Ok 'Backend operationnel.'
    }

    Write-Step "Frontend Streamlit sur http://${clientHost}:${FrontendPort}"
    # Les pages importent du code backend (from backend.app... ) : la racine du
    # depot doit etre dans PYTHONPATH pour que le paquet "backend" soit visible.
    $env:PYTHONPATH = $root
    if (-not $NoBrowser) { Start-Process "http://${clientHost}:${FrontendPort}" -ErrorAction SilentlyContinue }
    try {
        Push-Location $frontendDir
        & $venvPython @frontendArgs
    }
    finally {
        Pop-Location
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
        Write-Info 'Backend arrete.'
    }
    exit 0
}

# =============================================================================
# --- Mode par defaut : deux fenetres console dediees -------------------------
Write-Step "Backend FastAPI sur $backendUrl"
$bq = ConvertTo-SingleQuoted $backendDir
$pyq = ConvertTo-SingleQuoted $venvPython
$blq = ConvertTo-SingleQuoted $backendLog

$backendInner = @(
    "`$Host.UI.RawUI.WindowTitle = 'PMI Backend - uvicorn :$BackendPort'",
    "Set-Location -LiteralPath $bq",
    "`$env:PYTHONPATH = $bq",
    "& $pyq -m uvicorn app.main:app --host $ListenHost --port $BackendPort$reloadFlag 2>&1 | Tee-Object -FilePath $blq"
) -join '; '

$backendProc = Start-Process -FilePath 'powershell.exe' -PassThru -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $backendInner
)
Set-Content -LiteralPath (Join-Path $logDir 'backend.pid') -Value $backendProc.Id
Write-Ok "Backend demarre dans une nouvelle fenetre (PID $($backendProc.Id))."

if (-not $SkipHealth) {
    Write-Info "Attente de $backendUrl/health (jusqu'a $HealthTimeout s)..."
    if (-not (Wait-ForHttp -Url "$backendUrl/health" -TimeoutSeconds $HealthTimeout)) {
        Write-FailMsg "Le backend n'a pas repondu dans les $HealthTimeout s."
        Write-WarnMsg 'La fenetre "PMI Backend" affiche le detail. Dernieres lignes du log :'
        if (Test-Path -LiteralPath $backendLog) {
            Write-Host (Get-Content -LiteralPath $backendLog -Tail 30 | Out-String) -ForegroundColor Yellow
        }
        exit 1
    }
    Write-Ok 'Backend operationnel (/health repond 200).'
}

Write-Step "Frontend Streamlit sur http://${clientHost}:${FrontendPort}"
$fq = ConvertTo-SingleQuoted $frontendDir
$flq = ConvertTo-SingleQuoted $frontendLog

$rq = ConvertTo-SingleQuoted $root

$frontendInner = @(
    "`$Host.UI.RawUI.WindowTitle = 'PMI Frontend - Streamlit :$FrontendPort'",
    "Set-Location -LiteralPath $fq",
    "`$env:PYTHONPATH = $rq",
    "& $pyq -m streamlit run app.py --server.port $FrontendPort --server.address $ListenHost --server.headless true --browser.gatherUsageStats false 2>&1 | Tee-Object -FilePath $flq"
) -join '; '

$frontendProc = Start-Process -FilePath 'powershell.exe' -PassThru -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $frontendInner
)
Set-Content -LiteralPath (Join-Path $logDir 'frontend.pid') -Value $frontendProc.Id
Write-Ok "Frontend demarre dans une nouvelle fenetre (PID $($frontendProc.Id))."

Write-Info 'Attente du serveur Streamlit...'
if (-not (Wait-ForHttp -Url "http://${clientHost}:${FrontendPort}" -TimeoutSeconds 120)) {
    Write-WarnMsg "Streamlit n'a pas encore repondu. Verifiez la fenetre 'PMI Frontend'."
}
else {
    Write-Ok 'Frontend operationnel.'
}

if (-not $NoBrowser) {
    Start-Process "http://${clientHost}:${FrontendPort}" -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Green
Write-Host '  APPLICATION DEMARREE' -ForegroundColor Green
Write-Host '======================================================================' -ForegroundColor Green
Write-Block @(
    '',
    "  Interface   :  http://${clientHost}:${FrontendPort}",
    "  API Swagger :  $backendUrl/docs",
    "  Sante       :  $backendUrl/health",
    '',
    "  Logs        :  $backendLog",
    "                 $frontendLog",
    '',
    '  Arreter   :  .\stop.ps1',
    ''
) 'White'
exit 0
