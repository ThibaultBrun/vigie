import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import utide

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"


def _serie(code_station):
    params = {"code_entite": code_station, "grandeur_hydro": "H", "size": 20000, "sort": "asc"}
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    out = []
    for o in r.json().get("data", []):
        if o.get("resultat_obs") is None:
            continue
        s = o["date_obs"].replace("Z", "+00:00")
        dt = datetime.fromisoformat(s).astimezone(timezone.utc)
        out.append((dt, o["resultat_obs"] / 1000.0))
    return out


def pm_bm_jour(code_station, lat):
    serie = _serie(code_station)
    if len(serie) < 1000:
        return None
    t = np.array([np.datetime64(dt.replace(tzinfo=None), "s") for dt, _ in serie])
    h = np.array([v for _, v in serie], dtype=float)
    coef = utide.solve(t, h, lat=lat, method="ols", conf_int="none", verbose=False)

    maintenant = datetime.now(PARIS)
    debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = debut + timedelta(days=1)
    grille = np.arange(
        np.datetime64(debut.astimezone(timezone.utc).replace(tzinfo=None), "s"),
        np.datetime64(fin.astimezone(timezone.utc).replace(tzinfo=None), "s"),
        np.timedelta64(120, "s"),
    )
    rec = utide.reconstruct(grille, coef, verbose=False)
    hp = np.asarray(rec.h, dtype=float)

    d = np.diff(hp)
    pm_bm = []
    for i in range(1, len(d)):
        if d[i - 1] > 0 and d[i] <= 0:
            typ = "PM"
        elif d[i - 1] < 0 and d[i] >= 0:
            typ = "BM"
        else:
            continue
        ts = grille[i].astype("datetime64[s]").astype(datetime).replace(tzinfo=timezone.utc)
        local = ts.astimezone(PARIS)
        pm_bm.append({
            "type": typ,
            "heure_locale": local.isoformat(),
            "hauteur_m": round(float(hp[i]), 2),
        })
    return pm_bm
