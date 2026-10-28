param(
    [ValidateSet('prepare', 'run', 'fetch', 'test', 'audit', 'figures')]
    [string]$Command = 'run',
    [int]$Limit = 0,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $pythonExecutable = $venvPython
} elseif ($pythonCommand) {
    $pythonExecutable = $pythonCommand.Source
} else {
    $pythonExecutable = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExecutable)) {
        throw 'Python 3.10+ is required. Install Python or provide it on PATH.'
    }
}
if ($Command -eq 'test') {
    & $pythonExecutable -m unittest discover -s tests -v
} elseif ($Command -eq 'audit') {
    & $pythonExecutable scripts/audit_outputs.py
} elseif ($Command -eq 'figures') {
    foreach ($script in @('scripts/plot_total_summary.py', 'scripts/plot_integrated_network.py', 'scripts/audit_figures.py')) {
        & $pythonExecutable $script
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} else {
    $pipelineArguments = @('-m', 'biomed.pipeline', $Command)
    if ($Limit -gt 0) { $pipelineArguments += @('--limit', $Limit) }
    if ($Offline) { $pipelineArguments += '--offline' }
    & $pythonExecutable @pipelineArguments
}
exit $LASTEXITCODE
