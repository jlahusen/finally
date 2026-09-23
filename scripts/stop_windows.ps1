# Stop and remove the FinAlly container. Data in db\ is kept.
docker stop finally *> $null
docker rm finally *> $null
Write-Host "FinAlly stopped. Data in db\ is preserved."
