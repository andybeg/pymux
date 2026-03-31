param(
    [string]$PythonExe = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Installing pymux for Python 3.13/3.14 on Windows..."

& $PythonExe -m pip install -e .
& $PythonExe -m pip install pywinpty pyte
& $PythonExe -m pip install --no-deps git+https://github.com/prompt-toolkit/ptterm.git
& $PythonExe scripts/patch_ptterm_win.py

Write-Host "Done. Try: $PythonExe -m pymux --help"
