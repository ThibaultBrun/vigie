from datetime import datetime
from zoneinfo import ZoneInfo
from .config import charger_site
from .sources import hubeau, openmeteo

PARIS = ZoneInfo("Europe/Paris")


def construire(site_id):
    site = charger_site(site_id)
    notes = []
    maree = _bloc(_maree, site, notes, "maree")
    debit = _bloc(_debit, site, notes, "debit")
    meteo = _bloc(_meteo, site, notes, "meteo")
    danger = _danger(debit)
    return {
        "point": {"nom": site["nom"], "lat": site["lat"], "lon": site["lon"]},
        "horodatage": datetime.now(PARIS).isoformat(),
        "maree": maree,
        "debit": debit,
        "meteo": meteo,
        "danger": danger,
        "notes": notes,
    }


def _bloc(fn, site, notes, nom):
    try:
        return fn(site)
    except Exception as e:
        notes.append(f"{nom}: source indisponible ({type(e).__name__})")
        return {"disponible": False}


def _maree(site):
    cfg = site["maree"]
    obs = hubeau.niveau_observe(cfg["station_observee"], cfg["station_nom"])
    if obs is None:
        return {"disponible": False}
    return {
        "disponible": True,
        "phase": obs["phase"],
        "niveau_observe_m": obs["niveau_m"],
        "source_niveau": obs["source"],
        "horodatage_niveau": obs["horodatage"],
        "pm_bm": [],
        "coefficient": None,
        "source_coef": cfg.get("port_coef"),
    }


def _debit(site):
    cfg = site["debit"]
    d = hubeau.debit(cfg["station"], cfg["station_nom"], cfg)
    if d is None:
        return {"disponible": False}
    d["disponible"] = True
    return d


def _meteo(site):
    m = openmeteo.meteo(site["lat"], site["lon"])
    m["disponible"] = True
    return m


def _danger(debit):
    messages = []
    if debit.get("disponible") and debit.get("palier") == "eleve":
        messages.append(f"Débit Nive élevé : {debit.get('valeur_m3s')} m³/s")
    return {"actif": len(messages) > 0, "messages": messages}
