<#
.SYNOPSIS
    Arrete le backend et le frontend lances par start.ps1.

.DESCRIPTION
    - Termine les processus enregistres dans .\logs\pids.json (fenetres ou arriere-plan),
      ainsi que leurs processus enfants (python / worker uvicorn --reload).
    - Libere les ports du projet (8000 / 8501 par defaut) s'ils sont encore occupes
      par un python du .venv du projet. Aucun autre programme n'est touche.

.EXAMPLE
    .\stop.ps1
    .\stop.ps1 -BackendPort 8010 -FrontendPort 8511
#>
[CmdletBinding()]
param(
    [int] $BackendPort = 0,
    [int] $FrontendPort = 0
)

$ErrorActionPreference = "SilentlyContinue"
$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root
. (Join-Path $Root "scripts\windows\common.ps1")

Write-Banner "Power Market Intelligence Agent - Arret"

$PidFile = Join-Path $Root "logs\pids.json"
$script:stopped = 0

function Stop-Tree([int] $ProcessId) {
    if (-not $ProcessId) { return }
    # Enfants enumeres AVANT d'arreter le parent (Windows ne re-parente pas les orphelins,
    # la liste reste valide), parent arrete EN PREMIER (un superviseur comme
    # `uvicorn --reload` ne peut ainsi pas relancer son worker entre-temps).
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue)
    $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        $script:stopped++
    }
    foreach ($c in $children) { Stop-Tree ([int]$c.ProcessId) }
}

# 1. Processus enregistres par start.ps1
if (Test-Path $PidFile) {
    try {
        $json = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($name in @("backend", "frontend")) {
            $pidValue = $json.$name
            if (-not $pidValue) { continue }
            $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
            if (-not $proc) { continue }                                  # deja termine (fenetre fermee)
            if ($proc.ProcessName -notmatch '^(powershell|pwsh|python|pythonw)$') {
                Write-Warn "PID $pidValue ($($proc.ProcessName)) n'est plus un processus du projet - ignore."
                continue
            }
            Write-Info "Arret $name (PID $pidValue)"
            Stop-Tree ([int]$pidValue)
        }
        if ($BackendPort -le 0 -and $json.backend_port)   { $BackendPort  = [int]$json.backend_port }
        if ($FrontendPort -le 0 -and $json.frontend_port) { $FrontendPort = [int]$json.frontend_port }
    } catch { }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

if ($BackendPort -le 0) {
    $dotenv = Read-DotEnv (Join-Path $Root ".env")
    $BackendPort = Get-DotEnvInt $dotenv "BACKEND_PORT" 8000
}
if ($FrontendPort -le 0) {
    if (-not $dotenv) { $dotenv = Read-DotEnv (Join-Path $Root ".env") }
    $FrontendPort = Get-DotEnvInt $dotenv "FRONTEND_PORT" 8501
}

# 2. Processus du projet qui ecoutent encore sur les ports
$VenvDir = (Join-Path $Root ".venv")
$PortableDir = (Join-Path $Root ".python")
$hasNetTcp = [bool](Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)
foreach ($port in @($BackendPort, $FrontendPort)) {
    if (-not $hasNetTcp) { break }
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if (-not $proc) { continue }
        $path = $proc.Path
        $isProject = $path -and ($path.StartsWith($VenvDir, [StringComparison]::OrdinalIgnoreCase) -or $path.StartsWith($PortableDir, [StringComparison]::OrdinalIgnoreCase))
        if ($isProject) {
            Write-Info "Liberation du port $port (PID $($proc.Id))"
            Stop-Tree ([int]$proc.Id)
        } elseif ($proc.ProcessName -match "python") {
            Write-Warn "Port $port occupe par un python hors projet (PID $($proc.Id), $path) - non arrete."
        }
    }
}

if ($script:stopped -gt 0) { Write-Ok "$($script:stopped) processus arrete(s)." } else { Write-Ok "Aucun processus a arreter." }
