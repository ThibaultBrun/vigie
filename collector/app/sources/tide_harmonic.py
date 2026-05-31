import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import utide

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"


def _serie(code_station):
    params = {"code_entite": code_station, "grandeur_hydro": "H", "size": 20000, "sort": "asc"}
    derniere = None
    r = None
    for _ in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=(10, 90))
            r.raise_for_status()
            break
        except requests.RequestException as e:
            derniere = e
            r = None
    if r is None:
        raise derniere
    out = []
    for o in r.json().get("data", []):
        if o.get("resultat_obs") is None:
            continue
        s = o["date_obs"].replace("Z", "+00:00")
        dt = datetime.fromisoformat(s).astimezone(timezone.utc)
        out.append((dt, o["resultat_obs"] / 1000.0))
    return out


def _local_iso(grille, i):
    ts = grille[i].astype("datetime64[s]").astype(datetime).replace(tzinfo=timezone.utc)
    return ts.astimezone(PARIS).isoformat()


def analyser(code_station, lat):
    serie = _serie(code_station)
    if len(serie) < 1000:
        return None
    t = np.array([np.datetime64(dt.replace(tzinfo=None), "s") for dt, _ in serie])
    h = np.array([v for _, v in serie], dtype=float)
    coef = utide.solve(t, h, lat=lat, method="ols", conf_int="none", verbose=False)

    maintenant = datetime.now(PARIS)
    debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = debut + timedelta(days=7)
    grille = np.arange(
        np.datetime64(debut.astimezone(timezone.utc).replace(tzinfo=None), "s"),
        np.datetime64(fin.astimezone(timezone.utc).replace(tzinfo=None), "s"),
        np.timedelta64(300, "s"),
    )
    rec = utide.reconstruct(grille, coef, verbose=False)
    hp = np.asarray(rec.h, dtype=float)

    d = np.diff(hp)
    extrema = []
    for i in range(1, len(d)):
        if d[i - 1] > 0 and d[i] <= 0:
            extrema.append((i, "PM"))
        elif d[i - 1] < 0 and d[i] >= 0:
            extrema.append((i, "BM"))
    pm_bm = [{"type": typ, "heure_locale": _local_iso(grille, i), "hauteur_m": round(float(hp[i]), 2)} for i, typ in extrema]

    fenetre = 6
    courbe = []
    n = len(hp)
    for i in range(0, n, 3):
        proche, best = None, fenetre + 1
        for idx, typ in extrema:
            dd = abs(idx - i)
            if dd < best:
                best, proche = dd, typ
        if proche is not None and best <= fenetre:
            phase = "étale haute" if proche == "PM" else "étale basse"
        elif i + 1 < n and hp[i + 1] > hp[i]:
            phase = "montante"
        elif i + 1 < n and hp[i + 1] < hp[i]:
            phase = "descendante"
        elif i > 0 and hp[i] < hp[i - 1]:
            phase = "descendante"
        elif i > 0 and hp[i] > hp[i - 1]:
            phase = "montante"
        else:
            phase = "étale"
        courbe.append({"heure_locale": _local_iso(grille, i), "niveau_m": round(float(hp[i]), 2), "phase": phase})

    return {"pm_bm": pm_bm, "courbe": courbe}
