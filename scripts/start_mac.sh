#!/usr/bin/env bash
# Start FinAlly in Docker. Usage: scripts/start_mac.sh [--build] [--open]
set -euo pipefail

cd "$(dirname "$0")/.."
IMAGE=finally
CONTAINER=finally
URL=http://localhost:8000

BUILD=false
OPEN=false
for arg in "$@"; do
  case "$arg" in
    --build) BUILD=true ;;
    --open) OPEN=true ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

if $BUILD || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" .
fi

docker stop "$CONTAINER" >/dev/null 2>&1 || true
docker rm "$CONTAINER" >/dev/null 2>&1 || true

ENV_ARGS=()
[ -f .env ] && ENV_ARGS=(--env-file .env)

mkdir -p db
docker run -d --name "$CONTAINER" \
  -p 8000:8000 \
  -v "$PWD/db:/app/db" \
  ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} \
  "$IMAGE" >/dev/null

echo "FinAlly is running at $URL"

if $OPEN; then
  if command -v open >/dev/null; then open "$URL"; else xdg-open "$URL" >/dev/null 2>&1 || true; fi
fi
