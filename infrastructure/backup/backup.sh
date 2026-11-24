#!/bin/sh
set -eu
umask 077
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "backups/$stamp.dump"
docker compose exec -T web tar -C /app -czf - private > "backups/$stamp-media.tar.gz"
sha256sum backups/$stamp* > "backups/$stamp.sha256"
