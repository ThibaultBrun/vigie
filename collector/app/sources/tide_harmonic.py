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


def analyser(code_station, lat, seuil_renverse_mph=0.15):
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

    fenetre = 9
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

    # Renverse de courant (étale) : modèle provisoire dη/dt.
    # La marée fait basculer le courant un peu APRÈS la PM/BM. On estime la
    # bascule à l'instant où la vitesse de variation du niveau |dη/dt| dépasse
    # un seuil (le courant de marée l'emporte alors sur l'inertie/le débit).
    # Seuil non encore calibré sur le terrain ; à terme il dépendra du débit.
    dt_h = 300 / 3600.0

    def _rate(i):
        a = max(0, i - 1)
        b = min(n - 1, i + 1)
        return (hp[b] - hp[a]) / ((b - a) * dt_h)

    renverse = []
    for k, (i, typ) in enumerate(extrema):
        j_fin = extrema[k + 1][0] if k + 1 < len(extrema) else n - 1
        cible = -1 if typ == "PM" else 1  # après PM le jusant (dη/dt<0) s'installe
        trouve = None
        for j in range(i + 1, j_fin):
            r = _rate(j)
            if (cible < 0 and r <= -seuil_renverse_mph) or (cible > 0 and r >= seuil_renverse_mph):
                trouve = j
                break
        if trouve is None and j_fin > i + 1:  # marée trop molle : repli sur le |dη/dt| max
            trouve = max(range(i + 1, j_fin), key=lambda j: abs(_rate(j)))
        if trouve is not None:
            renverse.append({
                "heure_locale": _local_iso(grille, trouve),
                "sens": "flot→jusant" if typ == "PM" else "jusant→flot",
                "ref": typ,
                "ref_heure_locale": _local_iso(grille, i),
            })

    return {"pm_bm": pm_bm, "courbe": courbe, "renverse": renverse}
