#!/usr/bin/env python3
"""Ingestion serveur-à-serveur des activités Strava -> table strava_activite.

Guardé par STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET / STRAVA_REFRESH_TOKEN
(+ DATABASE_URL). Tant que ces variables ne sont pas définies, le script ne
fait rien — il devient actif dès qu'on dispose d'un refresh token au scope
`activity:read_all` (obtenu via une autorisation Strava unique).

Rafraîchit l'access token, pagine /athlete/activities, upsert par id Strava.
À planifier ~1×/jour (les sorties ne changent pas toutes les 5 min).
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    import psycopg
except ImportError:
    psycopg = None

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def _access_token(cid, cs, rt):
    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": cs,
        "grant_type": "refresh_token", "refresh_token": rt,
    }).encode()
    with urllib.request.urlopen(TOKEN_URL, data=data, timeout=30) as r:
        return json.load(r)


def _page(access_token, page, per_page=100):
    url = f"{ACTIVITIES_URL}?per_page={per_page}&page={page}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    cid = os.environ.get("STRAVA_CLIENT_ID")
    cs = os.environ.get("STRAVA_CLIENT_SECRET")
    rt = os.environ.get("STRAVA_REFRESH_TOKEN")
    url = os.environ.get("DATABASE_URL")
    if not (cid and cs and rt and url and psycopg):
        print("Strava/DB non configuré (token scope activité requis) — ingestion ignorée")
        return

    tok = _access_token(cid, cs, rt)
    access_token = tok.get("access_token")
    if "activity:read" not in (tok.get("scope") or ""):
        print(f"Scope insuffisant ({tok.get('scope')}) — il faut activity:read_all. Abandon.")
        return

    rows = []
    page = 1
    while page <= 30:  # garde-fou (~3000 activités max)
        acts = _page(access_token, page)
        if not acts:
            break
        for a in acts:
            rows.append((
                a["id"], (a.get("athlete") or {}).get("id"), a.get("type"),
                a.get("name"), a.get("start_date"), a.get("distance"),
                a.get("moving_time"), a.get("elapsed_time"), a.get("average_speed"),
                (a.get("map") or {}).get("summary_polyline"), json.dumps(a),
            ))
        page += 1
        time.sleep(1)  # respect des quotas

    if not rows:
        print("Aucune activité récupérée")
        return

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "insert into strava_activite (id, athlete_id, type, nom, start_date, "
                "distance_m, moving_time_s, elapsed_time_s, average_speed, polyline, raw) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
                rows,
            )
        conn.commit()
    print(f"{len(rows)} activités traitées")


if __name__ == "__main__":
    main()
