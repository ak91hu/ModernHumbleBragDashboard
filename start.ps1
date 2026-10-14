$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$portablePython = Join-Path $projectPath '.runtime\python\python.exe'
$pythonPath = if (Test-Path -LiteralPath $portablePython) { $portablePython } else { (Get-Command python -ErrorAction Stop).Source }
Push-Location -LiteralPath $projectPath
try {
    & $pythonPath app.py
} finally {
    Pop-Location
}
