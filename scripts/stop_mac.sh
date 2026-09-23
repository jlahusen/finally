#!/usr/bin/env bash
# Stop and remove the FinAlly container. Data in db/ is kept.
set -euo pipefail

docker stop finally >/dev/null 2>&1 || true
docker rm finally >/dev/null 2>&1 || true
echo "FinAlly stopped. Data in db/ is preserved."
