<#
    Fonctions partagees par setup.ps1 / start.ps1 / stop.ps1 / test.ps1
    (dot-source : `. .\scripts\windows\common.ps1`)

    Compatible Windows PowerShell 5.1 (livre avec Windows 10/11) et PowerShell 7+.
    Fichier volontairement en ASCII pur (PowerShell 5.1 lit les .ps1 sans BOM
    dans la page de code ANSI).
#>

# Versions de Python supportees (wheels precompilees disponibles pour toutes les deps)
$script:PythonMinMinor = 10   # 3.10
$script:PythonMaxMinor = 12   # 3.12
$script:PythonPortableVersion = "3.11.9"

# ----------------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------------
function Write-Banner([string] $Text) {
    $line = "=" * [Math]::Max(60, $Text.Length + 4)
    Write-Host ""
    Write-Host $line -ForegroundColor DarkCyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host $line -ForegroundColor DarkCyan
}
function Write-Step([string] $Num, [string] $Text) { Write-Host ""; Write-Host "[$Num] $Text" -ForegroundColor Yellow }
function Write-Ok([string] $Text)   { Write-Host "  [OK]   $Text" -ForegroundColor Green }
function Write-Info([string] $Text) { Write-Host "  [..]   $Text" -ForegroundColor Gray }
function Write-Warn([string] $Text) { Write-Host "  [!!]   $Text" -ForegroundColor DarkYellow }
function Write-Fail([string] $Text) { Write-Host "  [ERR]  $Text" -ForegroundColor Red }

function Test-IsAdmin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $p = New-Object Security.Principal.WindowsPrincipal($id)
        return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch { return $false }
}

# Echappe une chaine pour l'inclure entre apostrophes dans du code PowerShell
# (gere les chemins contenant une apostrophe, ex. C:\Users\O'Brien\...)
function ConvertTo-PSQuoted([string] $Text) {
    return "'" + $Text.Replace("'", "''") + "'"
}

# Quote un argument pour une ligne de commande Windows (regles CommandLineToArgvW),
# necessaire car Start-Process -ArgumentList joint les elements par des espaces
# SANS les quoter (un chemin contenant un espace serait coupe en deux).
function ConvertTo-ArgvQuoted([string] $Arg) {
    if ($null -eq $Arg -or $Arg -eq "") { return '""' }
    if ($Arg -notmatch '[\s"]') { return $Arg }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $backslashes = 0
    foreach ($ch in $Arg.ToCharArray()) {
        if ($ch -eq [char]92) { $backslashes++; continue }          # backslash
        if ($ch -eq [char]34) {                                      # double quote
            [void]$sb.Append([string]::new([char]92, $backslashes * 2 + 1))
            [void]$sb.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) { [void]$sb.Append([string]::new([char]92, $backslashes)); $backslashes = 0 }
        [void]$sb.Append($ch)
    }
    if ($backslashes -gt 0) { [void]$sb.Append([string]::new([char]92, $backslashes * 2)) }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function ConvertTo-ArgvLine([string[]] $Arguments) {
    return (($Arguments | ForEach-Object { ConvertTo-ArgvQuoted $_ }) -join " ")
}

# ----------------------------------------------------------------------------
# Execution de commandes natives (python.exe, pip...)
#
# Sous Windows PowerShell 5.1, si $ErrorActionPreference = "Stop" et que la
# sortie d'erreur d'un programme est redirigee (2>&1 / 2>$null), la moindre
# ligne ecrite sur stderr (un simple warning Python) devient une erreur fatale.
# Ces helpers executent la commande avec la preference "Continue" et renvoient
# le code de sortie ; la sortie (stdout+stderr) est renvoyee sous forme de texte.
# ----------------------------------------------------------------------------
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)] [string] $Exe,
        [string[]] $Arguments = @(),
        [switch] $Quiet
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = 0
    try {
        if ($Quiet) {
            $out = & $Exe @Arguments 2>&1 | ForEach-Object { "$_" }
            $code = $LASTEXITCODE
            return [pscustomobject]@{ ExitCode = $code; Output = ($out -join "`n") }
        } else {
            # Out-Host : la sortie est affichee en direct et n'est PAS capturee
            # dans la valeur de retour de la fonction (stderr va directement a la console).
            & $Exe @Arguments | Out-Host
            $code = $LASTEXITCODE
            return [pscustomobject]@{ ExitCode = $code; Output = "" }
        }
    } catch {
        return [pscustomobject]@{ ExitCode = 1; Output = "$($_.Exception.Message)" }
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Test-PythonModule([string] $Exe, [string] $Module) {
    $r = Invoke-Native -Exe $Exe -Arguments @("-c", "import $Module") -Quiet
    return ($r.ExitCode -eq 0)
}

# ----------------------------------------------------------------------------
# Reseau / proxy d'entreprise
# ----------------------------------------------------------------------------
function Show-ProxyHint {
    Write-Host ""
    Write-Host "  Si vous etes derriere un proxy d'entreprise, definissez avant de relancer :" -ForegroundColor DarkGray
    Write-Host '    $env:HTTPS_PROXY = "http://proxy.entreprise.local:8080"' -ForegroundColor DarkGray
    Write-Host '    $env:HTTP_PROXY  = $env:HTTPS_PROXY' -ForegroundColor DarkGray
    Write-Host "  Si le proxy fait de l'inspection SSL (certificat interne), creez %APPDATA%\pip\pip.ini :" -ForegroundColor DarkGray
    Write-Host "    [global]" -ForegroundColor DarkGray
    Write-Host "    trusted-host = pypi.org files.pythonhosted.org" -ForegroundColor DarkGray
    Write-Host '  Depot PyPI interne (Artifactory/Nexus) :  $env:PIP_INDEX_URL = "https://.../simple"' -ForegroundColor DarkGray
    Write-Host "  Details : docs\WINDOWS_SETUP.md (section Depannage)" -ForegroundColor DarkGray
    Write-Host ""
}

function Initialize-Tls {
    # PowerShell 5.1 utilise parfois TLS 1.0 par defaut -> echec des telechargements HTTPS
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    } catch { }
    # Utilise le proxy systeme + identifiants Windows (SSO proxy d'entreprise)
    try {
        $proxy = [Net.WebRequest]::GetSystemWebProxy()
        $proxy.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials
        [Net.WebRequest]::DefaultWebProxy = $proxy
    } catch { }
}

function Invoke-Download([string] $Url, [string] $Destination) {
    Initialize-Tls
    Write-Info "Telechargement : $Url"
    $dir = Split-Path -Parent $Destination
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $prevProgress = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"   # accelere fortement Invoke-WebRequest sous PS 5.1
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
        return (Test-Path $Destination)
    } catch {
        Write-Warn "Telechargement echoue : $($_.Exception.Message)"
        return $false
    } finally {
        $ProgressPreference = $prevProgress
    }
}

# ----------------------------------------------------------------------------
# Detection de Python
# ----------------------------------------------------------------------------
function Get-PythonVersionInfo([string] $Exe) {
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $null }
    $code = "import sys,platform; print('%d %d %d %s' % (sys.version_info[0], sys.version_info[1], sys.version_info[2], platform.architecture()[0]))"
    $r = Invoke-Native -Exe $Exe -Arguments @("-c", $code) -Quiet
    if ($r.ExitCode -ne 0 -or -not $r.Output) { return $null }
    $lastLine = ($r.Output -split "`n" | Where-Object { $_ -match '^\d+ \d+ \d+ ' } | Select-Object -Last 1)
    if (-not $lastLine) { return $null }
    $parts = $lastLine.Trim().Split(" ")
    return [pscustomobject]@{
        Exe   = $Exe
        Major = [int]$parts[0]
        Minor = [int]$parts[1]
        Patch = [int]$parts[2]
        Arch  = $parts[3]
    }
}

function Test-PythonSupported($Info) {
    if (-not $Info) { return $false }
    return ($Info.Major -eq 3 -and $Info.Minor -ge $script:PythonMinMinor -and $Info.Minor -le $script:PythonMaxMinor -and $Info.Arch -eq "64bit")
}

function Test-PythonVersion([string] $Exe) {
    return (Test-PythonSupported (Get-PythonVersionInfo $Exe))
}

function Find-Python([string] $Root) {
    $candidates = New-Object System.Collections.Generic.List[string]

    # 0. Python portable du projet (installe par -Portable)
    $portable = Join-Path $Root ".python\python.exe"
    if (Test-Path $portable) { $candidates.Add($portable) }

    # 1. Python Launcher (py.exe) : connait toutes les installations enregistrees
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($minor in ($script:PythonMaxMinor)..($script:PythonMinMinor)) {
            $r = Invoke-Native -Exe $py.Source -Arguments @("-3.$minor", "-c", "import sys; print(sys.executable)") -Quiet
            if ($r.ExitCode -eq 0 -and $r.Output) {
                $exe = ($r.Output -split "`n" | Select-Object -Last 1).Trim()
                if ($exe -and (Test-Path -LiteralPath $exe)) { $candidates.Add($exe) }
            }
        }
    }

    # 2. python.exe / python3.exe dans le PATH
    #    Les alias generiques du Microsoft Store (%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe
    #    et python3.exe) ne sont JAMAIS executes : si aucun Python Store n'est installe,
    #    les invoquer ouvre le Microsoft Store. Les alias versionnes (python3.11.exe)
    #    n'existent que si le paquet Store correspondant est reellement installe.
    foreach ($name in @("python.exe", "python3.exe", "python3.12.exe", "python3.11.exe", "python3.10.exe")) {
        Get-Command $name -All -ErrorAction SilentlyContinue | ForEach-Object {
            $src = $_.Source
            if (-not $src) { return }
            $isStoreAlias = ($src -like "*\Microsoft\WindowsApps\*")
            if ($isStoreAlias -and ($name -eq "python.exe" -or $name -eq "python3.exe")) { return }
            $candidates.Add($src)
        }
    }

    # 3. Emplacements classiques (installation utilisateur, sans admin)
    $roots = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles",
        "${env:ProgramFiles(x86)}",
        "C:\",
        "$env:USERPROFILE\scoop\apps\python\current",
        "$env:USERPROFILE\miniconda3", "$env:USERPROFILE\anaconda3",
        "$env:LOCALAPPDATA\miniconda3", "$env:LOCALAPPDATA\anaconda3",
        "$env:ProgramData\miniconda3", "$env:ProgramData\anaconda3"
    )
    foreach ($r in $roots) {
        if (-not $r -or -not (Test-Path $r)) { continue }
        Get-ChildItem -Path $r -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^Python3(10|11|12)(-64)?$' } |
            ForEach-Object {
                $exe = Join-Path $_.FullName "python.exe"
                if (Test-Path $exe) { $candidates.Add($exe) }
            }
        $direct = Join-Path $r "python.exe"
        if (Test-Path $direct) { $candidates.Add($direct) }
    }

    # 4. Python du Microsoft Store (installable sans admin) : detecte via les paquets
    #    Appx de l'utilisateur ; l'alias par famille de paquet n'existe que si le
    #    paquet est reellement installe (aucun risque d'ouvrir le Store).
    #    (Windows PowerShell uniquement : sous PowerShell 7 le module Appx passe par
    #    une session de compatibilite bruyante ; l'etape 2 couvre deja ce cas.)
    if ($PSVersionTable.PSEdition -eq "Desktop") {
        try {
            $pkgs = @(Get-AppxPackage -Name "PythonSoftwareFoundation.Python.3.1*" -ErrorAction SilentlyContinue)
            foreach ($pkg in $pkgs) {
                if (-not $pkg.PackageFamilyName) { continue }
                $exe = Join-Path $env:LOCALAPPDATA ("Microsoft\WindowsApps\" + $pkg.PackageFamilyName + "\python.exe")
                if (Test-Path $exe) { $candidates.Add($exe) }
            }
        } catch { }
    }

    # Premier candidat valide (3.10-3.12, 64 bits) ; preference 3.11 > 3.12 > 3.10
    $valid = @()
    foreach ($c in ($candidates | Select-Object -Unique)) {
        $v = Get-PythonVersionInfo $c
        if (Test-PythonSupported $v) { $valid += $v }
    }
    if ($valid.Count -eq 0) { return $null }
    $pref = @{ 11 = 0; 12 = 1; 10 = 2 }
    $best = $valid | Sort-Object { $pref[[int]$_.Minor] }, { -$_.Patch } | Select-Object -First 1
    return $best.Exe
}

# ----------------------------------------------------------------------------
# Installation de Python sans droits admin
# ----------------------------------------------------------------------------
function Install-PythonForCurrentUser([string] $Root) {
    <#
        Installeur officiel python.org en mode "Just for me" :
        - InstallAllUsers=0  -> %LOCALAPPDATA%\Programs\Python\Python311 (aucune elevation UAC)
        - PrependPath=1      -> ajoute Python au PATH de l'utilisateur
        - Include_test=0     -> plus leger
    #>
    $ver = $script:PythonPortableVersion
    $url = "https://www.python.org/ftp/python/$ver/python-$ver-amd64.exe"
    $installer = Join-Path $env:TEMP "python-$ver-amd64.exe"

    if (-not (Test-Path $installer)) {
        if (-not (Invoke-Download -Url $url -Destination $installer)) { return $null }
    }

    $verParts = $ver.Split(".")
    $target = Join-Path $env:LOCALAPPDATA ("Programs\Python\Python" + $verParts[0] + $verParts[1])
    Write-Info "Installation de Python $ver pour l'utilisateur courant (sans admin) dans $target"
    $installArgs = @("/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "Include_launcher=1", "InstallLauncherAllUsers=0", "SimpleInstall=1")
    try {
        $proc = Start-Process -FilePath $installer -ArgumentList $installArgs -Wait -PassThru
    } catch {
        Write-Warn "Impossible de lancer l'installeur : $($_.Exception.Message)"
        return $null
    }
    if ($proc.ExitCode -ne 0) {
        Write-Warn "L'installeur a retourne le code $($proc.ExitCode) (bloque par une politique de securite ?)."
        return $null
    }
    $exe = Join-Path $target "python.exe"
    if (Test-Path $exe) { return $exe }
    # Le PATH du processus courant n'est pas rafraichi : on cherche explicitement
    return (Find-Python -Root $Root)
}

function Install-PortablePython([string] $Root) {
    <#
        Python "portable" : le paquet officiel publie par la Python Software
        Foundation sur nuget.org (meme build que python.org), qui est un Python
        complet AVEC pip et venv, extrait dans .\.python\.
        Aucun installeur, aucune ecriture dans le registre, aucun droit admin.
        (Le paquet "embeddable" de python.org n'inclut ni pip ni venv : on l'evite.)
    #>
    $ver = $script:PythonPortableVersion
    $dest = Join-Path $Root ".python"
    $exe = Join-Path $dest "python.exe"
    if (Test-Path $exe) {
        if (Test-PythonVersion $exe) { Write-Ok "Python portable deja present : $exe"; return $exe }
        Remove-Item -Recurse -Force $dest
    }

    $nupkg = Join-Path $env:TEMP "python.$ver.nupkg"
    if (-not (Test-Path $nupkg)) {
        $urls = @(
            "https://www.nuget.org/api/v2/package/python/$ver",
            "https://globalcdn.nuget.org/packages/python.$ver.nupkg"
        )
        $ok = $false
        foreach ($u in $urls) {
            if (Invoke-Download -Url $u -Destination $nupkg) { $ok = $true; break }
        }
        if (-not $ok) { return $null }
    }

    # Extraction sur le meme volume que le projet (Move-Item instantane).
    # On utilise System.IO.Compression plutot qu'Expand-Archive : sous PS 5.1,
    # Expand-Archive gere mal les entrees comme "[Content_Types].xml" (crochets
    # interpretes comme des caracteres generiques) presentes dans tout .nupkg.
    $tmp = Join-Path $Root ".python-extract"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Write-Info "Extraction dans $dest"
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
        [System.IO.Compression.ZipFile]::ExtractToDirectory($nupkg, $tmp)
    } catch {
        Write-Warn "Extraction impossible : $($_.Exception.Message)"
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
        return $null
    }
    $tools = Join-Path $tmp "tools"
    if (-not (Test-Path (Join-Path $tools "python.exe"))) {
        Write-Warn "Archive inattendue (pas de tools\python.exe)."
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
        return $null
    }
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }   # reliquat d'une extraction interrompue
    Move-Item $tools $dest
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue

    # S'assure que pip est present
    if (-not (Test-PythonModule $exe "pip")) {
        Write-Info "Activation de pip (ensurepip)"
        Invoke-Native -Exe $exe -Arguments @("-m", "ensurepip", "--upgrade") -Quiet | Out-Null
    }
    if (Test-PythonVersion $exe) { Write-Ok "Python portable installe : $exe"; return $exe }
    return $null
}

function Request-PythonInstall([string] $Root) {
    Write-Host ""
    Write-Host "  Comment installer Python 3.11 (aucun droit administrateur requis) ?" -ForegroundColor Cyan
    Write-Host "    [1] Installeur officiel python.org, mode 'pour moi uniquement' (recommande)"
    Write-Host "    [2] Python portable dans le dossier du projet (.\.python\) - rien d'installe sur le systeme"
    Write-Host "    [3] Annuler (je l'installe moi-meme)"
    $choice = Read-Host "  Votre choix [1/2/3] (defaut 1)"
    if (-not $choice) { $choice = "1" }
    switch ($choice) {
        "1" {
            $exe = Install-PythonForCurrentUser -Root $Root
            if (-not $exe) {
                Write-Warn "Installeur indisponible ou bloque. Tentative en mode portable..."
                $exe = Install-PortablePython -Root $Root
            }
            return $exe
        }
        "2" { return (Install-PortablePython -Root $Root) }
        default {
            Write-Host ""
            Write-Host "  Installez Python 3.11 (64 bits) depuis https://www.python.org/downloads/windows/" -ForegroundColor Cyan
            Write-Host "  -> Cochez 'Add python.exe to PATH', decochez 'Use admin privileges', puis relancez .\setup.ps1"
            return $null
        }
    }
}

# ----------------------------------------------------------------------------
# Environnement virtuel / reseau local / processus
# ----------------------------------------------------------------------------
function Get-VenvPython([string] $Root) {
    $exe = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $exe) { return $exe }
    return $null
}

function Test-PortInUse([int] $Port) {
    # 1. Table des sockets en ecoute (toutes adresses : 0.0.0.0, 127.0.0.1, ::1...)
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($c) { return $true }
        return $false
    }
    # 2. Repli : tentative de bind sur 127.0.0.1
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $false
    } catch { return $true }
}

function Test-HttpUp([string] $Url, [int] $TimeoutMs = 3000) {
    # Requete HTTP locale SANS passer par le proxy systeme (sinon un proxy
    # d'entreprise peut intercepter localhost et faire echouer le test).
    try {
        $req = [System.Net.HttpWebRequest]::Create($Url)
        $req.Proxy = $null
        $req.Timeout = $TimeoutMs
        $req.ReadWriteTimeout = $TimeoutMs
        $req.Method = "GET"
        $resp = $req.GetResponse()
        $resp.Close()
        return $true
    } catch [System.Net.WebException] {
        # Une reponse HTTP (meme 4xx/5xx) prouve que le serveur ecoute
        if ($_.Exception.Response) { return $true }
        return $false
    } catch { return $false }
}

function Wait-HttpReady([string] $Url, [int] $TimeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpUp $Url) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Read-DotEnv([string] $Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in (Get-Content $Path -Encoding UTF8)) {
        $t = "$line".Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $idx = $t.IndexOf("=")
        if ($idx -lt 1) { continue }
        $k = $t.Substring(0, $idx).Trim()
        $v = $t.Substring($idx + 1).Trim().Trim('"').Trim("'")
        $map[$k] = $v
    }
    return $map
}

function Get-DotEnvInt($Map, [string] $Key, [int] $Default) {
    if ($Map -and $Map.ContainsKey($Key) -and "$($Map[$Key])" -match '^\d+$') { return [int]$Map[$Key] }
    return $Default
}
