#!/usr/bin/env bash
# 每日备份 SQLite 与 uploads
# crontab: 0 3 * * * /srv/rollax/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
stamp=$(date +%Y%m%d)
sqlite3 data/site.db ".backup backups/site-$stamp.db"
tar czf "backups/uploads-$stamp.tar.gz" uploads/
ls -t backups/site-*.db | tail -n +15 | xargs -r rm        # 保留 14 天
ls -t backups/uploads-*.tar.gz | tail -n +15 | xargs -r rm
echo "备份完成: site-$stamp.db / uploads-$stamp.tar.gz"
