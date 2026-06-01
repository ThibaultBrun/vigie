#!/usr/bin/env bash
set -e
cd /home/debian/repos/vigie/web
echo "→ build…"; npm run build >/dev/null
echo "→ déploiement prod (préserve data/ live)…"
rsync -a --delete --exclude data dist/ /srv/www/vigie/
chmod -R a+rX /srv/www/vigie
echo "✅ vigie promu en prod : https://vigie.tbrun.dev"
