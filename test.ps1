<#
.SYNOPSIS
    Execute la suite de tests du backend (pytest).

.EXAMPLE
    .\test.ps1
    .\test.ps1 -PytestArgs '-k market_analysis -vv'
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PytestArgs = '-v',
    [switch]$InstallDeps
)

. (Join-Path $PSScriptRoot 'scripts\win\Common.ps1')

$root = Get-RepoRoot
$backendDir = Join-Path $root 'backend'
$venvPython = Get-VenvPython

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-FailMsg "Environnement virtuel introuvable : $venvPython"
    Write-Host '    Lancez d''abord :  .\setup.ps1 -WithDev' -ForegroundColor Yellow
    exit 1
}

if ($InstallDeps) {
    $devReq = Join-Path $root 'backend\requirements-dev.txt'
    Write-Info "pip install -r $devReq"
    & $venvPython -m pip install -r $devReq --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { Write-FailMsg 'Installation des dependances de test echouee.'; exit 1 }
}

Write-Step 'pytest - backend'
$env:PYTHONPATH = $backendDir
$env:PYTHONIOENCODING = 'utf-8'
$extra = @()
if ($PytestArgs) { $extra = ($PytestArgs -split '\s+') }

Push-Location $backendDir
try {
    & $venvPython -m pytest tests @extra
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

Write-Host ''
if ($code -eq 0) { Write-Ok 'Tous les tests passent.' }
else { Write-FailMsg "pytest a retourne le code $code." }
exit $code
