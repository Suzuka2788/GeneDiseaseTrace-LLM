param(
    [ValidateSet('prepare', 'run', 'fetch', 'test', 'audit', 'figures')]
    [string]$Command = 'run',
    [int]$Limit = 0,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot
$env:PYTHONIOENCODING = 'utf-8'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
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
    & $pythonExecutable baseline/audit_outputs.py
} elseif ($Command -eq 'figures') {
    foreach ($script in @('baseline/plot_total_summary.py', 'baseline/plot_integrated_network.py', 'baseline/audit_figures.py')) {
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
