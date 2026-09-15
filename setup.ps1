<#
.SYNOPSIS
    Installation du Power Market Intelligence Agent sous Windows - 100% natif,
    sans droits administrateur.

.DESCRIPTION
    1. Detecte un Python 3.10 - 3.12 (64 bits) deja installe (py launcher, PATH,
       emplacements utilisateur classiques). Si aucun n'est trouve, propose une
       installation "pour moi uniquement" (sans admin) ou un Python portable
       dans .\.python\ (rien d'installe sur le systeme).
    2. Cree un environnement virtuel .venv a la racine du projet.
    3. Installe les dependances backend + frontend depuis requirements.txt,
       versions transitives verrouillees par constraints.txt (wheels
       precompilees uniquement : aucune compilation, aucun Visual C++).
       Si un dossier .\wheelhouse\ existe (prepare par
       scripts\make_wheelhouse.py), il est utilise en priorite.
    4. Cree le fichier .env (copie de .env.example) et les dossiers de travail.
    5. Verifie que l'application s'importe correctement.

.PARAMETER Python
    Chemin explicite vers un python.exe (ex: C:\Users\moi\AppData\Local\Programs\Python\Python311\python.exe).

.PARAMETER Portable
    Force l'utilisation d'un Python portable dans .\.python\ (telecharge si absent).

.PARAMETER Dev
    Installe aussi les outils de developpement (pytest, black, flake8).

.PARAMETER Offline
    Aucun acces reseau : Python doit deja etre present et les dependances sont
    installees uniquement depuis .\wheelhouse\ (pip --no-index).
    Preparation sur un poste connecte :  python scripts\make_wheelhouse.py --platform win_amd64 --python-version 3.11

.PARAMETER Force
    Recree l'environnement virtuel .venv meme s'il existe deja.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -Dev
    .\setup.ps1 -Python "C:\Python311\python.exe"
    .\setup.ps1 -Portable
    .\setup.ps1 -Offline      (poste sans acces a PyPI, avec .\wheelhouse\)

.NOTES
    Si l'execution des scripts est bloquee ("l'execution de scripts est desactivee") :
        powershell -ExecutionPolicy Bypass -File .\setup.ps1
    ou double-cliquez sur setup.cmd.
#>
[CmdletBinding()]
param(
    [string] $Python = "",
    [switch] $Portable,
    [switch] $Dev,
    [switch] $Offline,
    [switch] $Force
)

$ErrorActionPreference = "Stop"

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root
. (Join-Path $Root "scripts\windows\common.ps1")

Write-Banner "Power Market Intelligence Agent - Installation Windows"

# --- Verifications preliminaires -------------------------------------------
if (-not (Test-Path (Join-Path $Root "requirements.txt")) -or -not (Test-Path (Join-Path $Root "constraints.txt")) -or -not (Test-Path (Join-Path $Root "backend\app\main.py"))) {
    Write-Fail "requirements.txt / constraints.txt / backend\app\main.py introuvables. Lancez ce script depuis la racine du depot."
    exit 1
}
$Wheelhouse = Join-Path $Root "wheelhouse"
$HasWheelhouse = (Test-Path $Wheelhouse) -and @(Get-ChildItem -Path $Wheelhouse -Filter "*.whl" -ErrorAction SilentlyContinue).Count -gt 0
if ($Offline -and -not $HasWheelhouse) {
    Write-Fail "-Offline : aucun wheel dans $Wheelhouse. Preparez-le sur un poste connecte :"
    Write-Info "    python scripts\make_wheelhouse.py --platform win_amd64 --python-version 3.11"
    exit 1
}
# Versions de Python (3.10 / 3.11 / 3.12) et plateformes couvertes par le wheelhouse :
# les wheels compilees (numpy, pandas, pydantic-core...) sont propres a UNE version.
$WheelhouseInfo = $null
[int[]] $WheelhouseMinors = @()
if ($HasWheelhouse) {
    $WheelhouseInfo = Get-WheelhouseInfo $Wheelhouse
    $WheelhouseMinors = [int[]] $WheelhouseInfo.PythonMinors
}
function Test-WheelhouseCovers($Info) {
    # Vrai si le Python decrit par $Info (Get-PythonVersionInfo) peut etre servi par le wheelhouse.
    if ($WheelhouseMinors.Count -eq 0) { return $true }
    return ($Info -and ($WheelhouseMinors -contains [int]$Info.Minor))
}
function Write-WheelhouseMismatch($Info) {
    $v = "$($Info.Major).$($Info.Minor)"
    Write-Fail "Le wheelhouse ($Wheelhouse) est prevu pour Python $(Format-PythonMinors $WheelhouseMinors) et non pour Python $v."
    Write-Info "Au choix : installez un Python couvert (python.org, 'Install for me only') et relancez  .\setup.ps1 -Offline -Python <chemin\python.exe>"
    Write-Info "ou regenerez le wheelhouse pour ce Python :  python scripts\make_wheelhouse.py --platform win_amd64 --python-version $v"
}
if (Test-IsAdmin) {
    Write-Warn "Script lance en tant qu'administrateur : ce n'est pas necessaire (et deconseille)."
}
if ($Root -match '[^\x00-\x7F]') {
    Write-Warn "Le chemin du projet contient des caracteres accentues ($Root). Cela fonctionne generalement, mais un chemin simple (ex: C:\Dev\Agent) evite des surprises."
}

# --- 1. Environnement virtuel existant ? --------------------------------------
Write-Step "1/5" "Environnement virtuel .venv"

$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if ($Force -and (Test-Path $VenvDir)) {
    Write-Info "Suppression de l'ancien .venv (-Force)"
    Remove-Item -Recurse -Force $VenvDir
}

$reuseVenv = $false
if (Test-Path $VenvPython) {
    $venvInfo = Get-PythonVersionInfo $VenvPython
    if ((Test-PythonSupported $venvInfo) -and (-not $Offline -or (Test-WheelhouseCovers $venvInfo))) {
        Write-Ok ".venv existant (Python $($venvInfo.Major).$($venvInfo.Minor).$($venvInfo.Patch)) reutilise."
        if ($Python -or $Portable) { Write-Warn "-Python / -Portable ignores : utilisez -Force pour recreer le .venv avec cet interpreteur." }
        else { Write-Info "Utilisez -Force pour le recreer." }
        $reuseVenv = $true
    } elseif (Test-PythonSupported $venvInfo) {
        Write-Fail ".venv existant (Python $($venvInfo.Major).$($venvInfo.Minor).$($venvInfo.Patch)) non couvert par le wheelhouse (Python $(Format-PythonMinors $WheelhouseMinors)) : inutilisable hors-ligne."
        Write-Info "Relancez avec -Force pour le recreer avec un Python couvert (ajoutez -Python <chemin\python.exe> si besoin),"
        Write-Info "ou regenerez le wheelhouse pour ce Python :  python scripts\make_wheelhouse.py --platform win_amd64 --python-version $($venvInfo.Major).$($venvInfo.Minor)"
        exit 1
    } else {
        Write-Warn ".venv existant invalide (Python desinstalle ou version non supportee) : recreation."
        Remove-Item -Recurse -Force $VenvDir
    }
} else {
    Write-Info "Aucun .venv : il sera cree a l'etape 2."
}

# --- 2. Python + creation du venv ------------------------------------------
Write-Step "2/5" "Interpreteur Python 3.10 - 3.12 (64 bits)"

if ($reuseVenv) {
    Write-Ok "Etape ignoree (venv existant)"
} else {
    $PythonExe = $null

    if ($Portable) {
        if ($Offline -and -not (Test-Path (Join-Path $Root ".python\python.exe"))) {
            Write-Fail "-Portable et -Offline : aucun Python portable present dans .\.python\."
            exit 1
        }
        $PythonExe = Install-PortablePython -Root $Root
        if (-not $PythonExe) { Write-Fail "Installation du Python portable impossible (reseau / proxy ?)."; Show-ProxyHint; exit 1 }
    } elseif ($Python) {
        if (-not (Test-Path -LiteralPath $Python)) { Write-Fail "Python introuvable : $Python"; exit 1 }
        $PythonExe = (Resolve-Path -LiteralPath $Python).Path
        $info = Get-PythonVersionInfo $PythonExe
        if (-not (Test-PythonSupported $info)) {
            $desc = if ($info) { "$($info.Major).$($info.Minor).$($info.Patch) $($info.Arch)" } else { "version indeterminee" }
            Write-Fail "Ce Python ($desc) n'est pas supporte : il faut un Python 3.10, 3.11 ou 3.12 en 64 bits."
            exit 1
        }
    } else {
        # Avec un wheelhouse, on privilegie un Python qu'il couvre (3.11 > 3.12 > 3.10 sinon)
        $PythonExe = Find-Python -Root $Root -PreferredMinors $WheelhouseMinors
        if (-not $PythonExe) {
            Write-Warn "Aucun Python 3.10 - 3.12 (64 bits) trouve sur ce poste."
            Write-Info "(Python 3.13+ ou 32 bits ne convient pas : pas de wheels pour numpy/pandas/pydantic)"
            if ($Offline) {
                Write-Fail "Mode -Offline : impossible de telecharger Python. Installez Python 3.11 (python.org, 'Install for me only')."
                exit 1
            }
            $PythonExe = Request-PythonInstall -Root $Root
            if (-not $PythonExe) {
                Write-Fail "Installation de Python impossible. Voir docs\WINDOWS_SETUP.md (section Depannage)."
                exit 1
            }
        }
    }

    $pyInfo = Get-PythonVersionInfo $PythonExe
    Write-Ok "Python $($pyInfo.Major).$($pyInfo.Minor).$($pyInfo.Patch) ($($pyInfo.Arch)) : $PythonExe"
    if ($WheelhouseMinors.Count -gt 0 -and -not (Test-WheelhouseCovers $pyInfo)) {
        if ($Offline) { Write-WheelhouseMismatch $pyInfo; exit 1 }
        Write-Warn "Le wheelhouse couvre Python $(Format-PythonMinors $WheelhouseMinors) : les wheels compilees pour Python $($pyInfo.Major).$($pyInfo.Minor) viendront de PyPI."
    }

    Write-Info "Creation du venv : $VenvDir"
    $r = Invoke-Native -Exe $PythonExe -Arguments @("-m", "venv", $VenvDir) -Quiet
    if ($r.ExitCode -ne 0 -or -not (Test-Path $VenvPython)) {
        Write-Fail "Creation du venv impossible : $($r.Output)"
        Write-Info "Alternative : .\setup.ps1 -Portable  (Python portable autonome dans le projet)"
        exit 1
    }
    Write-Ok "venv cree"
}

# --- 3. Dependances ---------------------------------------------------------
Write-Step "3/5" "Installation des dependances (backend + frontend)"

$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$venvPyDesc = (Invoke-Native -Exe $VenvPython -Arguments @("-c", "import sys; print('%d.%d' % sys.version_info[:2])") -Quiet).Output.Trim()

# Source des paquets : PyPI (ou index interne via PIP_INDEX_URL), wheelhouse local, ou les deux.
$pipSource = @()
if ($HasWheelhouse) {
    $pipSource += @("--find-links", $Wheelhouse)
    $whDesc = "$($WheelhouseInfo.Count) wheels"
    if ($WheelhouseMinors.Count -gt 0) { $whDesc += ", Python $(Format-PythonMinors $WheelhouseMinors), $(if ($WheelhouseInfo.Platforms) { $WheelhouseInfo.Platforms -join ' ' } else { 'plateforme inconnue' })" }
    if ($Offline) {
        $pipSource += @("--no-index")
        Write-Ok "Mode hors-ligne : wheels lues dans $Wheelhouse ($whDesc ; aucun acces reseau)"
        if ($WheelhouseInfo.Platforms -and ($WheelhouseInfo.Platforms -notcontains "windows-x64")) {
            Write-Fail "Ce poste est un Windows 64 bits mais le wheelhouse ne contient que : $($WheelhouseInfo.Platforms -join ', ')."
            Write-Info "Regenerez-le :  python scripts\make_wheelhouse.py --platform win_amd64 --python-version $venvPyDesc"
            exit 1
        }
    } else {
        Write-Ok "Wheelhouse detecte : $Wheelhouse ($whDesc ; PyPI utilise seulement pour les paquets absents)"
    }
}

Write-Info "Mise a jour de pip"
$r = Invoke-Native -Exe $VenvPython -Arguments (@("-m", "pip", "install", "--upgrade", "pip", "--quiet", "--disable-pip-version-check") + $pipSource)
if ($r.ExitCode -ne 0) {
    Write-Warn "Mise a jour de pip echouee (proxy ?). On continue avec la version existante."
    if (-not $Offline) { Show-ProxyHint }
}

# constraints.txt verrouille les dependances transitives (memes versions sur
# Windows / Linux / macOS, Python 3.10-3.12) : pas de "ca marche chez moi".
$pipArgs = @(
    "-m", "pip", "install",
    "--only-binary", ":all:",     # jamais de compilation locale (pas de Visual C++ requis)
    "-r", (Join-Path $Root "requirements.txt"),
    "-c", (Join-Path $Root "constraints.txt")
)
if ($Dev) { $pipArgs += @("-r", (Join-Path $Root "requirements-dev.txt")) }
$pipArgs += $pipSource

Write-Info "pip install --only-binary :all: -r requirements.txt -c constraints.txt$(if ($Dev) { ' -r requirements-dev.txt' })"
if (-not $Offline) { Write-Info "(premiere installation : ~400 Mo a telecharger, 2 a 5 minutes)" }
$r = Invoke-Native -Exe $VenvPython -Arguments $pipArgs
if ($r.ExitCode -ne 0) {
    Write-Fail "Installation des dependances echouee (code $($r.ExitCode))."
    if ($Offline) {
        $whPlatforms = if ($WheelhouseInfo.Platforms) { $WheelhouseInfo.Platforms -join ', ' } else { '?' }
        Write-Info "Le wheelhouse doit correspondre a Windows 64 bits et a ce Python ($venvPyDesc) ;"
        Write-Info "il contient : $whPlatforms / Python $(Format-PythonMinors $WheelhouseMinors). Pour le regenerer :"
        Write-Info "    python scripts\make_wheelhouse.py --platform win_amd64 --python-version $venvPyDesc"
    } else {
        Show-ProxyHint
        Write-Info "Verifiez aussi que la version de Python est 3.10, 3.11 ou 3.12 en 64 bits (pas 3.13+, pas 32 bits)."
    }
    exit 1
}
Write-Ok "Dependances installees"

# --- 4. Configuration -------------------------------------------------------
Write-Step "4/5" "Configuration (.env, dossiers de travail)"

$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root ".env.example") $EnvFile
    Write-Ok ".env cree a partir de .env.example (aucune cle API requise)"
} else {
    Write-Ok ".env existant conserve"
}

foreach ($d in @("backend\generated", "backend\data_samples", "logs")) {
    $p = Join-Path $Root $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}
Write-Ok "Dossiers backend\generated et logs prets"

# --- 5. Verification --------------------------------------------------------
Write-Step "5/5" "Verification de l'installation"

$checkScript = Join-Path $Root "scripts\check_install.py"
$r = Invoke-Native -Exe $VenvPython -Arguments @($checkScript) -Quiet
if ($r.ExitCode -ne 0) {
    Write-Fail "Verification echouee :"
    Write-Host $r.Output
    exit 1
}
foreach ($line in ($r.Output -split "`n")) { if ($line.Trim()) { Write-Ok $line.Trim() } }

Write-Host ""
Write-Banner "Installation terminee"
Write-Host "  Lancer l'application :  " -NoNewline; Write-Host ".\start.ps1" -ForegroundColor Cyan
Write-Host "  Frontend             :  http://localhost:8501"
Write-Host "  API (Swagger)        :  http://localhost:8000/docs"
Write-Host "  Tests                :  .\test.ps1"
Write-Host ""
Write-Host "  Optionnel : renseignez OPENAI_API_KEY / ANTHROPIC_API_KEY dans .env pour un LLM reel." -ForegroundColor DarkGray
Write-Host "  Sans cle, l'application fonctionne a 100% en mode fallback local." -ForegroundColor DarkGray
Write-Host ""
