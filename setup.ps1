<#
.SYNOPSIS
    Installe "Power Market Intelligence Agent" en natif Windows.

.DESCRIPTION
    Installe TOUT le projet en local, SANS Docker Desktop, SANS WSL et SANS
    droits administrateur :

      1. Detecte un Python 3.10-3.12 (64 bits). S'il est absent, telecharge la
         distribution officielle python.org "sans installation" et la dezippe
         dans .python\ (aucun installeur, aucune elevation, aucune cle registre).
      2. Cree l'environnement virtuel .venv\
      3. Installe les dependances backend (FastAPI) + frontend (Streamlit)
      4. Genere le fichier .env a partir de .env.example en neutralisant ce qui
         depend de Docker (DATABASE_URL pointe vers l'hote "postgres" du compose)
      5. Genere frontend\.streamlit\config.toml et les dossiers de sortie
      6. Lance un auto-diagnostic complet (scripts\win\doctor.py)

    PostgreSQL n'est PAS necessaire : aucun module du backend n'ouvre de
    connexion SQL. La persistance reelle est fichier (backend\generated\).

.EXAMPLE
    .\setup.ps1

.EXAMPLE
    .\setup.ps1 -WithDev -BackendPort 8080

.EXAMPLE
    .\setup.ps1 -Proxy "http://proxy.entreprise.com:8080"

.NOTES
    Si la strategie d'execution bloque le script, utilisez setup.bat
    (ou : powershell -ExecutionPolicy Bypass -File .\setup.ps1)
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 8501,
    [string]$Proxy,
    [string]$IndexUrl,
    [switch]$WithDev,
    [switch]$SkipDeps,
    [switch]$Recreate,
    [switch]$NoDownload
)

. (Join-Path $PSScriptRoot 'scripts\win\Common.ps1')

$root = Get-RepoRoot
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host '  Power Market Intelligence Agent - installation native Windows' -ForegroundColor Cyan
Write-Host '  (sans Docker Desktop, sans droits administrateur)' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Info "Depot : $root"

if ($IsLinux -or $IsMacOS) {
    throw "Ce script est reserve a Windows. Sur Linux/macOS voir docs/INSTALLATION.md."
}

# ---------------------------------------------------------------------------
Write-Step 'Etape 1/6 - Python'
# ---------------------------------------------------------------------------
$proxySetting = Get-ProxySetting -Proxy $Proxy
if ($proxySetting) { Write-Info "Proxy detecte : $proxySetting" }

try {
    $python = Ensure-Python -Proxy $proxySetting -NoDownload:$NoDownload
}
catch {
    Write-FailMsg $_.Exception.Message
    exit 1
}

# ---------------------------------------------------------------------------
Write-Step 'Etape 2/6 - Environnement virtuel'
# ---------------------------------------------------------------------------
try {
    $venvPython = New-ProjectVenv -PythonExe $python.Exe -Recreate:$Recreate
}
catch {
    Write-FailMsg $_.Exception.Message
    exit 1
}
Write-Ok "Interpreteur du projet : $venvPython"

# ---------------------------------------------------------------------------
Write-Step 'Etape 3/6 - Dependances Python'
# ---------------------------------------------------------------------------
if ($SkipDeps) {
    Write-Info 'Installation des dependances ignoree (-SkipDeps).'
}
else {
    Write-Info 'Mise a jour de pip / setuptools / wheel...'
    if (-not (Invoke-Pip -VenvPython $venvPython -PipArgs @('install', '--upgrade', 'pip', 'setuptools', 'wheel') -Proxy $proxySetting -IndexUrl $IndexUrl -Retries 1)) {
        Write-WarnMsg 'pip n''a pas pu etre mis a jour (on continue avec la version existante).'
    }

    $reqFiles = @(
        (Join-Path $root 'backend\requirements.txt'),
        (Join-Path $root 'frontend\requirements.txt')
    )
    if ($WithDev) { $reqFiles += (Join-Path $root 'backend\requirements-dev.txt') }

    foreach ($req in $reqFiles) {
        if (-not (Test-Path -LiteralPath $req)) {
            Write-WarnMsg "Fichier absent : $req"
            continue
        }
        Write-Info "pip install -r $req  (2 a 6 min la premiere fois)"
        if (-not (Invoke-Pip -VenvPython $venvPython -PipArgs @('install', '-r', $req) -Proxy $proxySetting -IndexUrl $IndexUrl)) {
            Write-FailMsg "Echec de l'installation de $req."
            Write-Block @(
                '',
                '  Causes frequentes en environnement restreint :',
                '    * Proxy obligatoire    -> .\setup.ps1 -Proxy "http://proxy:port"',
                '    * Index interne        -> .\setup.ps1 -IndexUrl "https://pypi.entreprise/simple"',
                '    * TLS/antivirus        -> relancer une seconde fois (le cache pip reprend)',
                ''
            ) 'Yellow'
            exit 1
        }
        Write-Ok "Dependances installees : $(Split-Path -Leaf $req)"
    }
}

# ---------------------------------------------------------------------------
Write-Step 'Etape 4/6 - Configuration (.env, Streamlit, dossiers)'
# ---------------------------------------------------------------------------
$envArgs = @(
    (Join-Path $root 'scripts\win\env_writer.py'),
    '--root', $root,
    '--backend-port', $BackendPort,
    '--frontend-port', $FrontendPort
)
if ($Recreate) { $envArgs += '--force' }
& $venvPython @envArgs
if ($LASTEXITCODE -ne 0) {
    Write-FailMsg 'La generation du .env a echoue.'
    exit 1
}

# ---------------------------------------------------------------------------
Write-Step 'Etape 5/6 - Verification des ports'
# ---------------------------------------------------------------------------
foreach ($p in @(@{ n = 'Backend'; v = $BackendPort }, @{ n = 'Frontend'; v = $FrontendPort })) {
    if (Test-PortInUse -Port $p.v) {
        Write-WarnMsg "Le port $($p.v) ($($p.n)) est deja utilise par un autre programme."
        Write-WarnMsg "Au lancement utilisez par exemple : .\start.ps1 -$($p.n)Port <autre_port>"
    }
    else {
        Write-Ok "Port $($p.v) ($($p.n)) disponible."
    }
}

# ---------------------------------------------------------------------------
Write-Step 'Etape 6/6 - Auto-diagnostic'
# ---------------------------------------------------------------------------
$doctorArgs = @(
    (Join-Path $root 'scripts\win\doctor.py'),
    '--root', $root,
    '--backend-port', $BackendPort,
    '--frontend-port', $FrontendPort
)
& $venvPython @doctorArgs
$doctorCode = $LASTEXITCODE

# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
if ($doctorCode -eq 0) {
    Write-Host '  INSTALLATION TERMINEE - DIAGNOSTIC OK' -ForegroundColor Green
}
else {
    Write-Host "  INSTALLATION TERMINEE - ERREUR(S) AU DIAGNOSTIC (code $doctorCode)" -ForegroundColor Yellow
    Write-Host '  Les lignes [FAIL] ci-dessus expliquent quoi corriger.' -ForegroundColor Yellow
}
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Block @(
    '',
    '  Lancer l''application :',
    '',
    "      .\start.ps1",
    '',
    "  Puis ouvrir :  http://127.0.0.1:$FrontendPort      (interface Streamlit)",
    "                 http://127.0.0.1:$BackendPort/docs  (API Swagger)",
    '',
    '  Arreter  : .\stop.ps1',
    '  Tests    : .\test.ps1',
    '  Guide    : docs\INSTALLATION_WINDOWS.md',
    ''
) 'White'

if ($doctorCode -ne 0) { exit $doctorCode }
exit 0
