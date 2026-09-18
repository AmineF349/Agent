# =============================================================================
#  Power Market Intelligence Agent - bibliotheque PowerShell partagee
# -----------------------------------------------------------------------------
#  Utilisee par : setup.ps1 / start.ps1 / stop.ps1 / test.ps1
#
#  Garanties :
#    * Aucune dependance a Docker / Docker Desktop / WSL.
#    * Aucune operation ne demande de droits administrateur : tout est installe
#      dans le dossier du depot (.venv\ et .python\).
#    * Compatible Windows PowerShell 5.1 (Windows 10/11) ET PowerShell 7+.
#      -> pas de "??" ni de "? :", pas de "&&", pas d'appels .NET non signables.
# =============================================================================

Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
# Acceleration majeure de Invoke-WebRequest sous Windows PowerShell 5.1
$ProgressPreference = 'SilentlyContinue'

# --- Chemins -----------------------------------------------------------------
# $PSScriptRoot = <repo>\scripts\win
$script:PMI_REPO_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Versions Python supportees (numpy 1.26.4 / pydantic-core 2.16.3 / polars
# 0.20.22 n'ont pas de wheel pour 3.13 -> on reste sur 3.10 - 3.12).
$script:PMI_PY_MIN_MINOR = 10
$script:PMI_PY_MAX_MINOR = 12
$script:PMI_PY_DEFAULT   = '3.11.9'

# URL officielles python.org (verifiees dans windows-3.11.9.json du projet CPython)
$script:PMI_PY_ZIP_URL = 'https://www.python.org/ftp/python/{0}/python-{0}-{1}.zip'
$script:PMI_PY_EXE_URL = 'https://www.python.org/ftp/python/{0}/python-{0}-{1}.exe'
$script:PMI_GETPIP_URL = 'https://bootstrap.pypa.io/get-pip.py'


# --- Affichage ---------------------------------------------------------------
function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "    [ OK ] $Message" -ForegroundColor Green
}

function Write-Info {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "    [ .. ] $Message" -ForegroundColor Gray
}

function Write-WarnMsg {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "    [WARN] $Message" -ForegroundColor Yellow
}

function Write-FailMsg {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "    [FAIL] $Message" -ForegroundColor Red
}

function Write-Block {
    param([Parameter(Mandatory = $true)][string[]]$Lines, [string]$Color = 'White')
    foreach ($l in $Lines) { Write-Host $l -ForegroundColor $Color }
}


# --- Chemins du projet -------------------------------------------------------
function Get-RepoRoot { return $script:PMI_REPO_ROOT }
function Get-VenvDir { return (Join-Path $script:PMI_REPO_ROOT '.venv') }
function Get-VenvPython { return (Join-Path (Get-VenvDir) 'Scripts\python.exe') }
function Get-PortablePythonDir { return (Join-Path $script:PMI_REPO_ROOT '.python') }
function Get-PortablePython { return (Join-Path (Get-PortablePythonDir) 'python.exe') }
function Get-ToolsDir { return (Join-Path $script:PMI_REPO_ROOT 'tools') }
function Get-LogDir {
    $d = Join-Path $script:PMI_REPO_ROOT 'logs'
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    return $d
}


# --- Reseau ------------------------------------------------------------------
function Test-PortInUse {
    <# Retourne $true si un serveur ecoute deja sur 127.0.0.1:$Port #>
    param([Parameter(Mandatory = $true)][int]$Port)
    try {
        $r = Test-NetConnection -ComputerName '127.0.0.1' -Port $Port `
            -InformationLevel Quiet -WarningAction SilentlyContinue
        return [bool]$r
    }
    catch {
        return $false
    }
}

function Wait-ForHttp {
    <# Attend qu'une URL reponde 200 (timeout en secondes). #>
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 120
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) { return $true }
        }
        catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-ProxySetting {
    <# Resout le proxy a passer a pip / Invoke-WebRequest. Priorite : parametre > env. #>
    param([string]$Proxy)
    if ($Proxy) { return $Proxy }
    if ($env:PMI_PROXY) { return $env:PMI_PROXY }
    if ($env:HTTPS_PROXY) { return $env:HTTPS_PROXY }
    if ($env:HTTP_PROXY) { return $env:HTTP_PROXY }
    if ($env:https_proxy) { return $env:https_proxy }
    if ($env:http_proxy) { return $env:http_proxy }
    return $null
}


# --- Detection / installation de Python --------------------------------------
function Get-PythonVersionOf {
    <# Retourne "3.11.9" ou $null si l'executable n'est pas un Python utilisable. #>
    param([Parameter(Mandatory = $true)][string]$Exe)
    if (-not $Exe) { return $null }
    if (-not (Test-Path -LiteralPath $Exe)) {
        # l'exe peut etre un nom dans le PATH (python, python3.11...)
        $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
        if (-not $cmd) { return $null }
        $Exe = $cmd.Source
    }
    # Le stub "python.exe" du Microsoft Store ouvre la boutique au lieu de
    # s'executer : on l'exclut explicitement.
    if ($Exe -match 'WindowsApps') { return $null }
    try {
        $out = & $Exe -c "import sys;print('%d.%d.%d' % sys.version_info[:3])" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $v = ($out | Out-String).Trim()
        if ($v -match '^\d+\.\d+\.\d+$') { return $v }
        return $null
    }
    catch {
        return $null
    }
}

function Test-PythonCompatible {
    <# Verifie version 3.10-3.12 + 64 bits (les wheels numpy/polars sont 64 bits). #>
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string]$Version
    )
    $parts = $Version.Split('.')
    if ($parts[0] -ne '3') { return $false }
    $minor = [int]$parts[1]
    if ($minor -lt $script:PMI_PY_MIN_MINOR -or $minor -gt $script:PMI_PY_MAX_MINOR) { return $false }
    try {
        $bits = (& $Exe -c "import struct;print(struct.calcsize('P')*8)" 2>$null | Out-String).Trim()
        if ($bits -ne '64') { return $false }
    }
    catch {
        return $false
    }
    return $true
}

function Resolve-Python {
    <#
      Cherche un Python 3.10-3.12 64 bits utilisable, sans rien installer.
      Ordre : PMI_PYTHON (override) > venv du projet > .python\ portable >
              lanceur "py" > PATH > dossiers d'installation classiques.
      Retourne [pscustomobject]@{ Exe; Version } ou $null.
    #>
    $candidates = @()
    if ($env:PMI_PYTHON) { $candidates += $env:PMI_PYTHON }
    $candidates += (Get-VenvPython)
    $candidates += (Get-PortablePython)

    # Lanceur "py.exe" (installe avec Python depuis la 3.3)
    $py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $lines = & 'py.exe' -0p 2>$null
            foreach ($l in $lines) {
                # ex: " -3.11-64       C:\Users\me\AppData\...\python.exe *"
                $line = ($l | Out-String).Trim()
                if ($line -match '^\*?\s*(-?V?-?3\.\d+)(-32|-64)?\s+(\S.*?)\s*\*?\s*$') {
                    $tag = $Matches[1]
                    $arch = $Matches[2]
                    $path = $Matches[3].Trim().Trim('*').Trim()
                    if ($arch -ne '-32') { $candidates += $tag }
                    if ($path) { $candidates += $path }
                }
            }
        }
        catch { }
    }

    $candidates += @('python.exe', 'python3.exe', 'python3.12.exe', 'python3.11.exe', 'python3.10.exe')

    $roots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        'C:\Python312', 'C:\Python311', 'C:\Python310',
        $env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}
    )
    foreach ($r in $roots) {
        if ($r -and (Test-Path -LiteralPath $r)) {
            foreach ($d in (Get-ChildItem -LiteralPath $r -Directory -ErrorAction SilentlyContinue)) {
                if ($d.Name -match '^Python3(10|11|12)$') {
                    $candidates += (Join-Path $d.FullName 'python.exe')
                }
            }
            if ($r -match 'Python3(10|11|12)$') {
                $candidates += (Join-Path $r 'python.exe')
            }
        }
    }

    $best = $null
    foreach ($c in $candidates) {
        $v = Get-PythonVersionOf -Exe $c
        if (-not $v) { continue }
        if (-not (Test-PythonCompatible -Exe $c -Version $v)) { continue }
        $resolved = $c
        if (Test-Path -LiteralPath $c) { $resolved = (Resolve-Path -LiteralPath $c).Path }
        else { $resolved = (Get-Command $c).Source }
        $obj = [pscustomobject]@{ Exe = $resolved; Version = $v }
        # Preference a 3.11 (version cible du projet), sinon la plus recente.
        if (-not $best) { $best = $obj; continue }
        if ($v.StartsWith('3.11.') -and -not $best.Version.StartsWith('3.11.')) { $best = $obj }
    }
    return $best
}

function Find-PythonInTree {
    <# Trouve python.exe dans une arborescence dezippee (layout independant). #>
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [int]$MaxDepth = 3
    )
    if (-not (Test-Path -LiteralPath $Root)) { return $null }
    $direct = Join-Path $Root 'python.exe'
    if (Test-Path -LiteralPath $direct) { return $direct }
    # -Depth est disponible depuis PowerShell 5.0 (Windows 10)
    $hit = Get-ChildItem -LiteralPath $Root -Recurse -Depth $MaxDepth -Filter 'python.exe' `
        -File -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if ($hit) { return $hit }
    return $null
}

function Install-PortablePython {
    <#
      Telecharge la distribution Windows officielle "sans installation"
      (python-x.y.z-amd64.zip) et la dezippe dans <repo>\.python\.
      -> zero droit admin, zero installeur, zero ecriture registre.
    #>
    param(
        [string]$Version = $script:PMI_PY_DEFAULT,
        [string]$Proxy
    )
    $arch = 'amd64'
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { $arch = 'arm64' }

    $dest = Get-PortablePythonDir
    $exe = Find-PythonInTree -Root $dest
    if ($exe -and (Get-PythonVersionOf -Exe $exe)) {
        Write-Ok "Python portable deja present : $exe"
        return $exe
    }

    $url = $script:PMI_PY_ZIP_URL -f $Version, $arch
    $toolsDir = Get-ToolsDir
    if (-not (Test-Path -LiteralPath $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null }
    $zip = Join-Path $toolsDir "python-$Version-$arch.zip"

    Write-Info "Telechargement : $url"
    Write-Info "Taille attendue ~33 Mo. Destination : $dest"
    try {
        $iwr = @{ Uri = $url; OutFile = $zip; UseBasicParsing = $true; TimeoutSec = 1800 }
        if ($Proxy) { $iwr['Proxy'] = $Proxy }
        Invoke-WebRequest @iwr
    }
    catch {
        Write-WarnMsg "Telechargement echoue ($($_.Exception.Message))."
        return $null
    }

    Write-Info 'Extraction (cela prend 1 a 2 minutes)...'
    try {
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force -ErrorAction SilentlyContinue }
        Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
    }
    catch {
        Write-WarnMsg "Extraction echouee ($($_.Exception.Message))."
        return $null
    }

    $exe = Find-PythonInTree -Root $dest
    if (-not $exe) {
        Write-WarnMsg "python.exe introuvable apres extraction dans $dest."
        return $null
    }

    # pip : la distribution complete embarque ensurepip.
    try { & $exe -m ensurepip --upgrade 2>&1 | Out-Null } catch { }
    $pipOk = $false
    try {
        & $exe -m pip --version 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $pipOk = $true }
    }
    catch { }

    if (-not $pipOk) {
        Write-Info 'ensurepip indisponible, fallback get-pip.py'
        $getpip = Join-Path $toolsDir 'get-pip.py'
        try {
            $iwr = @{ Uri = $script:PMI_GETPIP_URL; OutFile = $getpip; UseBasicParsing = $true; TimeoutSec = 300 }
            if ($Proxy) { $iwr['Proxy'] = $Proxy }
            Invoke-WebRequest @iwr
            & $exe $getpip --no-warn-script-location 2>&1 | Out-Null
        }
        catch {
            Write-WarnMsg "Impossible d'installer pip dans le Python portable."
            return $null
        }
    }

    Write-Ok "Python portable installe : $exe"
    return $exe
}

function Install-PythonPerUser {
    <#
      Plan B : installeur officiel .exe en mode "per-user".
      InstallAllUsers=0 -> aucune elevation, aucune demande UAC.
    #>
    param(
        [string]$Version = $script:PMI_PY_DEFAULT,
        [string]$Proxy
    )
    $arch = 'amd64'
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { $arch = 'arm64' }

    $dest = Join-Path (Get-ToolsDir) "Python$($Version.Replace('.', ''))"
    $toolsDir = Get-ToolsDir
    if (-not (Test-Path -LiteralPath $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null }
    $installer = Join-Path $toolsDir "python-$Version-$arch.exe"

    $url = $script:PMI_PY_EXE_URL -f $Version, $arch
    Write-Info "Telechargement installeur per-user : $url"
    try {
        $iwr = @{ Uri = $url; OutFile = $installer; UseBasicParsing = $true; TimeoutSec = 1800 }
        if ($Proxy) { $iwr['Proxy'] = $Proxy }
        Invoke-WebRequest @iwr
    }
    catch {
        Write-WarnMsg "Telechargement echoue ($($_.Exception.Message))."
        return $null
    }

    $exe = Join-Path $dest 'python.exe'
    Write-Info "Installation per-user vers $dest (aucune demande admin)"
    $psi = @(
        '/quiet',
        "InstallAllUsers=0",
        "TargetDir=$dest",
        'DefaultAllUsersTargetDir=0',
        'Include_launcher=0',
        'InstallLauncherAllUsers=0',
        'Include_test=0',
        'Include_doc=0',
        'Include_dev=0',
        'PrependPath=0',
        'AssociateFiles=0',
        'Shortcuts=0',
        'Include_pip=1'
    )
    try {
        $p = Start-Process -FilePath $installer -ArgumentList $psi -Wait -PassThru -NoNewWindow
        if ($p.ExitCode -ne 0) {
            Write-WarnMsg "Installeur Python : code retour $($p.ExitCode)."
            return $null
        }
    }
    catch {
        Write-WarnMsg "Installeur bloque par la politique de securite ? ($($_.Exception.Message))"
        return $null
    }

    if (Test-Path -LiteralPath $exe) {
        Write-Ok "Python per-user installe : $exe"
        return $exe
    }
    return $null
}

function Ensure-Python {
    <#
      Point d'entree : renvoie un [pscustomobject]@{ Exe; Version } garanti.
      Leve une exception explicite si aucun Python ne peut etre obtenu.
    #>
    param(
        [string]$Proxy,
        [switch]$NoDownload
    )
    $found = Resolve-Python
    if ($found) {
        Write-Ok "Python trouve : $($found.Exe)  (version $($found.Version))"
        return $found
    }

    Write-WarnMsg 'Aucun Python 3.10-3.12 (64 bits) detecte sur cette machine.'
    if ($NoDownload) {
        throw "Python 3.10-3.12 (64 bits) requis. Installez-le depuis https://www.python.org/downloads/windows/ ou passez la variable d'environnement PMI_PYTHON."
    }

    Write-Step 'Installation automatique de Python (sans droits administrateur)'
    $exe = Install-PortablePython -Version $script:PMI_PY_DEFAULT -Proxy $Proxy
    if (-not $exe) {
        Write-WarnMsg 'Le zip portable a echoue, essai de l''installeur per-user...'
        $exe = Install-PythonPerUser -Version $script:PMI_PY_DEFAULT -Proxy $Proxy
    }
    if (-not $exe) {
        throw "Impossible d'obtenir un Python utilisable. Installez Python 3.11 depuis https://www.python.org/downloads/windows/ (case 'Add python.exe to PATH') puis relancez .\setup.ps1"
    }
    $v = Get-PythonVersionOf -Exe $exe
    return [pscustomobject]@{ Exe = $exe; Version = $v }
}


# --- venv / pip --------------------------------------------------------------
function New-ProjectVenv {
    <# Cree <repo>\.venv (aucun droit admin requis). #>
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [switch]$Recreate
    )
    $venv = Get-VenvDir
    if ($Recreate -and (Test-Path -LiteralPath $venv)) {
        Write-Info "Suppression de l'ancien environnement : $venv"
        Remove-Item -LiteralPath $venv -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath (Get-VenvPython)) {
        Write-Ok "Environnement virtuel deja present : $venv"
        return (Get-VenvPython)
    }
    Write-Info "Creation de l'environnement virtuel : $venv"
    # Sortie capturee : une fonction PowerShell renvoie TOUT ce qui passe dans
    # le pipeline, la valeur retournee doit rester le seul chemin python.exe.
    $venvOutput = & $PythonExe -m venv $venv 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host $venvOutput -ForegroundColor Red
        throw "Echec de la creation du venv (code $LASTEXITCODE)."
    }
    if (-not (Test-Path -LiteralPath (Get-VenvPython))) { throw "venv cree mais python.exe introuvable dans $venv\Scripts." }
    Write-Ok "Environnement virtuel cree."
    return (Get-VenvPython)
}

function Invoke-Pip {
    <# pip install avec retries + proxy + index optionnels. #>
    param(
        [Parameter(Mandatory = $true)][string]$VenvPython,
        [Parameter(Mandatory = $true)][string[]]$PipArgs,
        [string]$Proxy,
        [string]$IndexUrl,
        [int]$Retries = 2
    )
    $base = @('-m', 'pip', '--disable-pip-version-check', '--no-input')
    if ($Proxy) { $base += @('--proxy', $Proxy) }
    if ($IndexUrl) { $base += @('--index-url', $IndexUrl) }
    $all = $base + $PipArgs

    for ($i = 0; $i -le $Retries; $i++) {
        & $VenvPython @all
        if ($LASTEXITCODE -eq 0) { return $true }
        Write-WarnMsg "pip a echoue (code $LASTEXITCODE). Tentative $($i + 1)/$($Retries + 1)."
        Start-Sleep -Seconds 3
    }
    return $false
}


# --- Fichier .env ------------------------------------------------------------
function Read-EnvFile {
    <# Parse .env -> hashtable (cles en majuscules, valeurs sans quotes). #>
    param([string]$Path)
    $map = @{}
    if (-not $Path) { $Path = Join-Path $script:PMI_REPO_ROOT '.env' }
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in (Get-Content -LiteralPath $Path)) {
        $t = ($line | Out-String).Trim()
        if (-not $t) { continue }
        if ($t.StartsWith('#')) { continue }
        $idx = $t.IndexOf('=')
        if ($idx -lt 1) { continue }
        $k = $t.Substring(0, $idx).Trim()
        $v = $t.Substring($idx + 1).Trim()
        if ($v.Length -ge 2) {
            if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
                $v = $v.Substring(1, $v.Length - 2)
            }
        }
        $map[$k] = $v
    }
    return $map
}

function Get-EnvFileValue {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$Path
    )
    $map = Read-EnvFile -Path $Path
    if ($map.ContainsKey($Key)) { return $map[$Key] }
    return $null
}

function Import-EnvFile {
    <#
      Charge .env dans l'environnement du processus courant (les processus fils
      en heritent). Important : pydantic-settings cherche ".env" relativement au
      repertoire de travail (backend\), donc le .env racine ne serait pas lu
      sans cette etape. Une variable deja presente dans l'environnement reel
      n'est jamais ecrasee (comportement standard de dotenv).
    #>
    param([string]$Path)
    $map = Read-EnvFile -Path $Path
    $applied = @()
    foreach ($k in $map.Keys) {
        $envPath = 'Env:' + $k
        if (-not (Test-Path -LiteralPath $envPath)) {
            Set-Item -Path $envPath -Value $map[$k]
            $applied += $k
        }
    }
    return $applied
}
