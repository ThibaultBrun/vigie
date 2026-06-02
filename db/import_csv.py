#!/usr/bin/env python3
"""Migration unique : CSV d'archive (collector/archive/*.csv) -> table observation.

Valeurs converties en SI (H mm->m, Q L/s->m³/s). Idempotent (ON CONFLICT DO NOTHING).
Usage : DATABASE_URL=... python db/import_csv.py
"""
import csv
import os
import pathlib
from datetime import datetime

import psycopg

REPO = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = REPO / "collector" / "archive"
# slug fichier -> (code station, grandeur)
MAP = {
    "convergent-adour-h": ("Q935001001", "H"),
    "pontblanc-nive-h": ("Q935251001", "H"),
    "cambo-nive-q": ("Q931251001", "Q"),
}


def main():
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        for slug, (code, grandeur) in MAP.items():
            f = ARCHIVE / f"{slug}.csv"
            if not f.exists():
                print(f"absent: {f.name}")
                continue
            rows = []
            with open(f, newline="", encoding="utf-8") as fh:
                for d, v in csv.reader(fh):
                    if d == "date_obs":
                        continue
                    ts = datetime.fromisoformat(d.replace("Z", "+00:00"))
                    rows.append((code, grandeur, ts, float(v) / 1000.0))
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into observation (station_code, grandeur, ts, valeur) "
                    "values (%s, %s, %s, %s) on conflict (station_code, ts) do nothing",
                    rows,
                )
            conn.commit()
            print(f"{slug}: {len(rows)} lignes traitées")
        with conn.cursor() as cur:
            cur.execute(
                "select station_code, count(*), min(ts), max(ts) from observation group by station_code order by station_code"
            )
            for r in cur.fetchall():
                print(r)


if __name__ == "__main__":
    main()
