#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed or is not available in PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: Docker Compose is not available." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is not running. Start Docker Desktop and try again." >&2
  exit 1
fi

echo "Building and starting Matrix One Market..."
docker compose up -d --build --remove-orphans

echo "Waiting for the web and API services..."
ready=false
for _ in $(seq 1 60); do
  if docker compose exec -T web \
    node -e 'const host = require("os").hostname(); fetch(`http://${host}:3000/api/v1/health`).then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))' \
    >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != "true" ]]; then
  echo "Error: services did not become ready within 60 seconds." >&2
  docker compose ps >&2
  docker compose logs --tail=100 api web >&2
  exit 1
fi

docker compose ps
echo
echo "Matrix One Market is ready."
echo "Service:   https://market.matrix-one.tech"
echo "Web:       http://127.0.0.1:7890"
echo "Direct API: http://127.0.0.1:7891/api/v1/health"
