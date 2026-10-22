# Regenerate backend/requirements.lock and backend/requirements-dev.lock.
#
# The locks pin every package to the version tested in the development
# environment (backend/constraints-tested.txt, a pip freeze of that
# environment) and resolve for the Docker image: Linux x86_64, Python 3.11,
# CPU torch from the PyTorch CPU index.
#
#   .\scripts\compile_requirements_lock.ps1                 # reuse constraints-tested.txt
#   .\scripts\compile_requirements_lock.ps1 -RefreshTested  # re-freeze the current venv first
#
# Needs uv (pip install uv). Run from any folder.

param(
    [switch]$RefreshTested
)

# uv reports progress on stderr; failures are detected from $LASTEXITCODE, so
# do not let Windows PowerShell turn that stderr text into terminating errors.
$ErrorActionPreference = "Continue"
$backend = Join-Path (Split-Path -Parent $PSScriptRoot) "backend"
$constraints = Join-Path $backend "constraints-tested.txt"

if ($RefreshTested) {
    # The development venv runs a torch nightly; pin the release it became.
    $frozen = python -m pip freeze --exclude-editable |
        Where-Object { $_ -match '^[A-Za-z0-9_.-]+==' -and $_ -notmatch '^(torch|torchvision)==' }
    $header = @(
        "# pip freeze of the environment the backend tests passed in (Windows, Python 3.11).",
        "# torch/torchvision: the development venv ran 2.12.0.dev20260408 / 0.27.0.dev20260407",
        "# nightlies; the released versions are pinned instead.",
        "torch==2.12.0",
        "torchvision==0.27.0"
    )
    # UTF-8 without a byte-order mark: pip reads constraint files as plain text.
    [IO.File]::WriteAllLines($constraints, [string[]]($header + $frozen), (New-Object Text.UTF8Encoding($false)))
}

$common = @(
    "--constraint", "constraints-tested.txt",
    "--python-version", "3.11",
    "--python-platform", "x86_64-manylinux_2_28",
    "--index-url", "https://pypi.org/simple",
    "--extra-index-url", "https://download.pytorch.org/whl/cpu",
    "--index-strategy", "unsafe-best-match",
    "--emit-index-url",
    "--annotation-style", "line"
)

Push-Location $backend
try {
    uv pip compile requirements-ml.txt @common -o requirements.lock
    if ($LASTEXITCODE -ne 0) { throw "uv pip compile (runtime) failed" }
    uv pip compile requirements-ml.txt requirements-dev.txt @common -o requirements-dev.lock
    if ($LASTEXITCODE -ne 0) { throw "uv pip compile (dev) failed" }
} finally {
    Pop-Location
}
Write-Host "Wrote backend/requirements.lock and backend/requirements-dev.lock"
