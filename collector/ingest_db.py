#!/usr/bin/env python3
"""Ingestion continue Hub'Eau -> Postgres (table observation).

Lancé sur le VPS par refresh.sh quand DATABASE_URL est défini (jamais en CI :
la base n'est joignable qu'en local). Tire une fenêtre glissante et upsert
(ON CONFLICT DO NOTHING). Valeurs en SI : H en m, Q en m³/s.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import requests

try:
    import psycopg
except ImportError:
    psycopg = None

BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"
STATIONS = [("Q935001001", "H"), ("Q935251001", "H"), ("Q931251001", "Q")]
JOURS = 7


def _tirer(code, grandeur):
    d0 = (datetime.now(timezone.utc) - timedelta(days=JOURS)).strftime("%Y-%m-%d")
    params = {"code_entite": code, "grandeur_hydro": grandeur, "size": 20000,
              "sort": "asc", "date_debut_obs": d0}
    for _ in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=(10, 90))
            r.raise_for_status()
            return r.json().get("data", [])
        except requests.RequestException:
            time.sleep(3)
    return []


def main():
    url = os.environ.get("DATABASE_URL")
    if not url or psycopg is None:
        print("DATABASE_URL/psycopg absent — ingestion DB ignorée")
        return
    with psycopg.connect(url) as conn:
        for code, grandeur in STATIONS:
            rows = []
            for o in _tirer(code, grandeur):
                if o.get("resultat_obs") is None:
                    continue
                ts = datetime.fromisoformat(o["date_obs"].replace("Z", "+00:00"))
                rows.append((code, grandeur, ts, o["resultat_obs"] / 1000.0))
            if not rows:
                continue
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into observation (station_code, grandeur, ts, valeur) "
                    "values (%s, %s, %s, %s) on conflict (station_code, ts) do nothing",
                    rows,
                )
            conn.commit()
            print(f"{code}/{grandeur}: {len(rows)} pts")


if __name__ == "__main__":
    main()
