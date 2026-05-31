import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"


def _get(params):
    derniere = None
    for _ in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=(10, 60))
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            derniere = e
    raise derniere


def _to_paris(s):
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(PARIS).isoformat()


def niveau_observe(code_station, station_nom, points=8):
    data = _get({"code_entite": code_station, "grandeur_hydro": "H", "size": points, "sort": "desc"})
    obs = [o for o in data.get("data", []) if o.get("resultat_obs") is not None]
    if not obs:
        return None
    dernier = obs[0]
    return {
        "niveau_m": round(dernier["resultat_obs"] / 1000.0, 3),
        "horodatage": _to_paris(dernier["date_obs"]),
        "phase": _phase(obs),
        "source": f"{station_nom} {code_station}",
    }


def _phase(obs):
    vals = [o["resultat_obs"] for o in obs]
    recents = vals[:6] if len(vals) >= 6 else vals
    if recents[0] > recents[-1]:
        return "montante"
    if recents[0] < recents[-1]:
        return "descendante"
    return "etale"


def debit(code_station, station_nom):
    data = _get({"code_entite": code_station, "grandeur_hydro": "Q", "size": 3, "sort": "desc"})
    obs = [o for o in data.get("data", []) if o.get("resultat_obs") is not None]
    if not obs:
        return None
    dernier = obs[0]
    return {
        "valeur_m3s": round(dernier["resultat_obs"] / 1000.0, 2),
        "source": f"{station_nom} {code_station}",
        "horodatage": _to_paris(dernier["date_obs"]),
    }
