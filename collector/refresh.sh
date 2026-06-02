#!/usr/bin/env bash
set -e
cd /home/debian/repos/vigie/collector
.venv/bin/python collect.py >/dev/null 2>&1
cp -f /home/debian/repos/vigie/web/public/data/*.json /srv/www/vigie/data/

# Ingestion historique en base (VPS uniquement, best-effort)
if [ -f /home/debian/repos/vigie/db/.env ]; then
  set -a; . /home/debian/repos/vigie/db/.env; set +a
  .venv/bin/python ingest_db.py >/dev/null 2>&1 || true
fi
