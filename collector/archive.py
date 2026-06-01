"""Archivage des séries Hub'Eau temps réel.

Hub'Eau (observations_tr) ne conserve qu'~1 mois de données haute fréquence.
Ce script tire le mois glissant des marégraphes et du débit, puis l'empile
dans des CSV append-only (déduplication par horodatage). Lancé périodiquement
(cf. .github/workflows/archive.yml), il accumule un historique long terme
servant à l'analyse marée × débit (décalage estuaire, renverse de courant).

Valeurs stockées brutes telles que renvoyées par Hub'Eau :
  - H (hauteur) en mm
  - Q (débit) en L/s
"""
import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"
ARCHIVE = Path(__file__).resolve().parent / "archive"

# (code_station, grandeur, slug fichier) — Bayonne / Nive-Adour
STATIONS = [
    ("Q935001001", "H", "convergent-adour-h"),   # embouchure Adour (≈ port)
    ("Q935251001", "H", "pontblanc-nive-h"),      # Pont Blanc, Nive (près du ponton)
    ("Q931251001", "Q", "cambo-nive-q"),          # débit Nive à Cambo-les-Bains
]


def tirer(code, grandeur):
    # Hub'Eau refuse date_debut < 1 mois : on prend 29 jours de marge.
    d0 = (datetime.now(timezone.utc) - timedelta(days=29)).strftime("%Y-%m-%d")
    params = {
        "code_entite": code, "grandeur_hydro": grandeur,
        "size": 20000, "sort": "asc", "date_debut_obs": d0,
    }
    derniere = None
    for _ in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=(10, 120))
            r.raise_for_status()
            return r.json().get("data", [])
        except requests.RequestException as e:
            derniere = e
            time.sleep(3)
    raise derniere


def empiler(slug, data):
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    chemin = ARCHIVE / f"{slug}.csv"
    rows = {}
    if chemin.exists():
        with open(chemin, newline="", encoding="utf-8") as f:
            for d, v in csv.reader(f):
                if d == "date_obs":
                    continue
                rows[d] = v
    avant = len(rows)
    for o in data:
        if o.get("resultat_obs") is None:
            continue
        rows[o["date_obs"]] = repr(o["resultat_obs"])
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date_obs", "resultat_obs"])
        for d in sorted(rows):
            w.writerow([d, rows[d]])
    print(f"{slug}: {len(rows)} lignes (+{len(rows) - avant})")


def main():
    for code, grandeur, slug in STATIONS:
        try:
            empiler(slug, tirer(code, grandeur))
        except Exception as e:
            print(f"{slug}: ECHEC ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
