#!/bin/bash
# Daily pg_dump of the nutrition database (schemas nutrition + food) with 14-day rotation.
set -euo pipefail
DEST=${NUTRITION_BACKUP_DIR:-$HOME/backups/nutrition}
mkdir -p "$DEST"
out="$DEST/nutrition-$(date +%F).dump"
# sudo -n: the systemd user manager may predate the docker group membership
sudo -n docker exec nutrition-db pg_dump -U postgres -Fc -d nutrition > "$out.tmp"
mv "$out.tmp" "$out"
find "$DEST" -name 'nutrition-*.dump' -mtime +14 -delete
echo "backup ok: $out ($(du -h "$out" | cut -f1))"
