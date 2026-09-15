<#
.SYNOPSIS
    Arrete le backend et le frontend demarres par .\start.ps1

.DESCRIPTION
    1. Relit les PID memorises dans logs\backend.pid et logs\frontend.pid et
       detruit l'arbre de processus complet (taskkill /T).
    2. En complement, recherche les processus orphelins dont la ligne de commande
       correspond a uvicorn (app.main:app) ou a Streamlit (app.py) de CE depot.

.EXAMPLE
    .\stop.ps1
    .\stop.ps1 -Force     # ne demande aucune confirmation
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Force
)

. (Join-Path $PSScriptRoot 'scripts\win\Common.ps1')

$root = Get-RepoRoot
$logDir = Get-LogDir
$repoNeedle = $root.TrimEnd('\')

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host '  Power Market Intelligence Agent - arret' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan

$stopped = 0

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId, [string]$Label)
    $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $p) {
        Write-Info "$Label : PID $ProcessId deja termine."
        return 0
    }
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
    Start-Sleep -Milliseconds 400
    $still = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($still) {
        Write-WarnMsg "$Label : PID $ProcessId toujours vivant."
        return 0
    }
    Write-Ok "$Label arrete (PID $ProcessId)."
    return 1
}

# --- 1) PID memorises --------------------------------------------------------
foreach ($item in @(@{ f = 'backend.pid'; l = 'Backend' }, @{ f = 'frontend.pid'; l = 'Frontend' })) {
    $pidFile = Join-Path $logDir $item.f
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $raw = (Get-Content -LiteralPath $pidFile | Out-String).Trim()
    $procId = 0
    if ($raw -match '^\d+$') { $procId = [int]$raw }
    if ($procId -gt 0) { $stopped += Stop-ProcessTree -ProcessId $procId -Label $item.l }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

# --- 2) Processus orphelins --------------------------------------------------
Write-Info 'Recherche de processus orphelins...'
try {
    $venvNeedle = (Get-VenvDir).TrimEnd('\')
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine } |
        Where-Object {
            $cl = $_.CommandLine
            $isPmiWindow = $cl.Contains('PMI Backend') -or $cl.Contains('PMI Frontend')
            $isRepoUvicorn = $cl.Contains('app.main:app') -and
                ($cl.Contains($repoNeedle) -or $cl.Contains($venvNeedle))
            $isRepoStreamlit = $cl.Contains('streamlit') -and $cl.Contains('run app.py') -and
                ($cl.Contains($repoNeedle) -or $cl.Contains($venvNeedle))
            $isPmiWindow -or $isRepoUvicorn -or $isRepoStreamlit
        }
    foreach ($proc in $procs) {
        $stopped += Stop-ProcessTree -ProcessId ([int]$proc.ProcessId) -Label "Orphelin $($proc.Name)"
    }
}
catch {
    Write-WarnMsg "Enumeration WMI indisponible ($($_.Exception.Message))."
}

Write-Host ''
if ($stopped -gt 0) {
    Write-Ok "$stopped processus arrete(s)."
}
else {
    Write-Info 'Aucun processus de l''application n''etait en cours.'
}
Write-Host ''
exit 0
