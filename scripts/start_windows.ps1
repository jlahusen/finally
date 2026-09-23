# Start FinAlly in Docker. Usage: scripts\start_windows.ps1 [-Build] [-Open]
param(
    [switch]$Build,
    [switch]$Open
)

Set-Location (Split-Path -Parent $PSScriptRoot)
$Image = "finally"
$Container = "finally"
$Url = "http://localhost:8000"

docker image inspect $Image *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

docker stop $Container *> $null
docker rm $Container *> $null

$EnvArgs = @()
if (Test-Path .env) { $EnvArgs = @("--env-file", ".env") }

New-Item -ItemType Directory -Force db | Out-Null
docker run -d --name $Container -p 8000:8000 -v "${PWD}\db:/app/db" @EnvArgs $Image | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "FinAlly is running at $Url"
if ($Open) { Start-Process $Url }
