<#
.SYNOPSIS
    Diagnostic de l'installation Windows : Python, dependances, .env, ports, services, reseau.

.DESCRIPTION
    Lance scripts\doctor.py avec le Python du .venv. Ne modifie rien.
    Code de sortie : 0 = installation saine, 1 = au moins un probleme bloquant.

.EXAMPLE
    .\doctor.ps1
    (copiez la sortie complete dans toute demande d'aide)
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root
. (Join-Path $Root "scripts\windows\common.ps1")

$VenvPython = Get-VenvPython $Root
if (-not $VenvPython) {
    Write-Fail "Environnement virtuel introuvable (.venv) : lancez .\setup.ps1"
    $py = Find-Python -Root $Root
    if ($py) { Write-Info "Python detecte pour setup.ps1 : $py" } else { Write-Info "Aucun Python 3.10-3.12 (64 bits) trouve : setup.ps1 propose de l'installer sans admin." }
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
# Appel direct (pas via Invoke-Native/Out-Host) : la sortie reste dans le flux standard,
# donc affichee a l'ecran ET capturable ( $out = .\doctor.ps1 ; .\doctor.ps1 > diag.txt ).
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $VenvPython (Join-Path $Root "scripts\doctor.py")
$code = $LASTEXITCODE
$ErrorActionPreference = $prev
exit $code
