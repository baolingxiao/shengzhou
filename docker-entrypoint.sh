#!/usr/bin/env sh
set -eu
if [ ! -f /app/data/characters/characters.json ]; then
  echo "[entrypoint] initializing /app/data from image defaults..."
  mkdir -p /app/data
  cp -a /app/data-default/. /app/data/
fi
exec "$@"
