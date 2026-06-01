#!/usr/bin/env bash
set -e
cd /home/debian/repos/vigie/collector
.venv/bin/python collect.py >/dev/null 2>&1
cp -f /home/debian/repos/vigie/web/public/data/*.json /srv/www/vigie/data/
