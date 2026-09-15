<#
.SYNOPSIS
    Lance la suite de tests backend (pytest) sous Windows.

.EXAMPLE
    .\test.ps1
    .\test.ps1 tests/test_market_analysis.py
    .\test.ps1 -- tests/test_market_analysis.py -k baseload -x
    (mettez "--" avant les options pytest pour que PowerShell ne les interprete pas)
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PytestArgs
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root
. (Join-Path $Root "scripts\windows\common.ps1")

$VenvPython = Get-VenvPython $Root
if (-not $VenvPython) { Write-Fail "Environnement virtuel introuvable. Lancez :  .\setup.ps1"; exit 1 }

if (-not (Test-PythonModule $VenvPython "pytest")) {
    Write-Info "pytest absent : installation des outils de dev (requirements-dev.txt)"
    $devArgs = @("-m", "pip", "install", "--only-binary", ":all:", "-r", (Join-Path $Root "requirements-dev.txt"), "-c", (Join-Path $Root "constraints.txt"))
    $wheelhouse = Join-Path $Root "wheelhouse"
    if ((Test-Path $wheelhouse) -and @(Get-ChildItem -Path $wheelhouse -Filter "*.whl" -ErrorAction SilentlyContinue).Count -gt 0) { $devArgs += @("--find-links", $wheelhouse) }
    $r = Invoke-Native -Exe $VenvPython -Arguments $devArgs
    if ($r.ExitCode -ne 0) { Write-Fail "Installation de pytest echouee."; Show-ProxyHint; exit 1 }
}

$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = Join-Path $Root "backend"
if (-not $PytestArgs -or $PytestArgs.Count -eq 0) { $PytestArgs = @("tests/", "-v") }

Write-Banner "pytest $($PytestArgs -join ' ')"
Push-Location (Join-Path $Root "backend")
try {
    $r = Invoke-Native -Exe $VenvPython -Arguments (@("-m", "pytest") + $PytestArgs)
    exit $r.ExitCode
} finally {
    Pop-Location
}
