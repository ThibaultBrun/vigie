from datetime import datetime
from zoneinfo import ZoneInfo
from .config import charger_site
from .sources import hubeau, openmeteo, tide_harmonic

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


METHODE_PM_BM = (
    "Heures estimées par analyse harmonique (utide) sur ~30 jours de mesures du "
    "marégraphe de Pont Blanc. Le marégraphe est en estuaire : la marée y arrive plus "
    "tard et atténuée par rapport au port de Boucau-Bayonne, et ce décalage varie avec "
    "le débit de la Nive et le coefficient. Caler le modèle sur Pont Blanc lui-même "
    "intègre nativement ce retard local. Le niveau observé reste prioritaire pour "
    "l'instant présent ; les résidus liés au débit ne sont pas corrigés."
)


def _maree(site):
    cfg = site["maree"]
    obs = hubeau.niveau_observe(cfg["station_observee"], cfg["station_nom"])
    if obs is None:
        return {"disponible": False}
    try:
        pm_bm = tide_harmonic.pm_bm_jour(cfg["station_observee"], site["lat"]) or []
    except Exception:
        pm_bm = []
    return {
        "disponible": True,
        "phase": obs["phase"],
        "niveau_observe_m": obs["niveau_m"],
        "source_niveau": obs["source"],
        "horodatage_niveau": obs["horodatage"],
        "pm_bm": pm_bm,
        "methode_pm_bm": METHODE_PM_BM,
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
