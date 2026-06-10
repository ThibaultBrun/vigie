from datetime import datetime
from zoneinfo import ZoneInfo
from .config import charger_site
from .sources import hubeau, openmeteo, tide_harmonic, webcam, maree_coef, debit_tendance

PARIS = ZoneInfo("Europe/Paris")


def construire(site_id):
    site = charger_site(site_id)
    notes = []
    maree = _bloc(_maree, site, notes, "maree")
    debit = _bloc(_debit, site, notes, "debit")
    meteo = _bloc(_meteo, site, notes, "meteo")
    webcam_data = _bloc(_webcam, site, notes, "webcam") if site.get("webcam") else None
    danger = _danger(debit, meteo)
    return {
        "point": {"nom": site["nom"], "lat": site["lat"], "lon": site["lon"]},
        "horodatage": datetime.now(PARIS).isoformat(),
        "maree": maree,
        "debit": debit,
        "meteo": meteo,
        "webcam": webcam_data,
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
    "Heures calculées par analyse harmonique des mesures du marégraphe de Pont Blanc "
    "(Nive) : le retard et l'atténuation de l'estuaire sont déjà intégrés. "
    "Le coefficient, lui, vient du port de Boucau-Bayonne."
)


METHODE_RENVERSE = (
    "Le courant bascule un peu après la pleine/basse mer : on l'estime à l'instant "
    "où le niveau varie assez vite pour que le courant de marée l'emporte. "
    "Modèle provisoire, pas encore calé sur le terrain — un ordre de grandeur."
)


def _maree(site):
    cfg = site["maree"]
    rev_cfg = cfg.get("renverse", {})
    obs = hubeau.niveau_observe(cfg["station_observee"], cfg["station_nom"])
    if obs is None:
        return {"disponible": False}
    try:
        analyse = tide_harmonic.analyser(
            cfg["station_observee"], site["lat"],
            seuil_renverse_mph=rev_cfg.get("seuil_m_par_h", 0.15),
        )
    except Exception:
        analyse = None
    pm_bm = analyse["pm_bm"] if analyse else []
    courbe = analyse["courbe"] if analyse else []
    renverse = analyse.get("renverse", []) if analyse else []
    phase = _phase_maintenant(obs["phase"], pm_bm, obs["horodatage"])
    try:
        jours = maree_coef.coefficients(cfg["maree_info_id"]) if cfg.get("maree_info_id") else None
    except Exception:
        jours = None
    coef_today = None
    if jours and jours[0]["coefficients"]:
        coef_today = max(jours[0]["coefficients"])
    return {
        "disponible": True,
        "phase": phase,
        "niveau_observe_m": obs["niveau_m"],
        "source_niveau": obs["source"],
        "horodatage_niveau": obs["horodatage"],
        "pm_bm": pm_bm,
        "courbe": courbe,
        "renverse": renverse,
        "methode_pm_bm": METHODE_PM_BM,
        "methode_renverse": METHODE_RENVERSE,
        "station_horaires": cfg.get("station_nom"),
        "coefficient": coef_today,
        "coefficients_jour": jours[0]["coefficients"] if jours else [],
        "coefficients_jours": jours or [],
        "source_coef": cfg.get("port_coef"),
    }


def _phase_maintenant(obs_phase, pm_bm, horodatage_niveau):
    if not pm_bm or not horodatage_niveau:
        return obs_phase
    t = datetime.fromisoformat(horodatage_niveau)
    for p in pm_bm:
        pt = datetime.fromisoformat(p["heure_locale"])
        if abs((pt - t).total_seconds()) <= 2700:
            return "étale haute" if p["type"] == "PM" else "étale basse"
    return obs_phase


def _debit(site):
    cfg = site["debit"]
    d = hubeau.debit(cfg["station"], cfg["station_nom"])
    if d is None:
        return {"disponible": False}
    v = d["valeur_m3s"]
    tl = cfg.get("tendance_latlon") or [site["lat"], site["lon"]]
    try:
        tend = debit_tendance.tendance(tl[0], tl[1])
    except Exception:
        tend = None
    nav = cfg.get("navigation_pirogue", {})
    emin = nav.get("echelle_min_m3s")
    emax = nav.get("echelle_max_m3s")
    position = None
    hors = False
    if emin is not None and emax is not None and emax > emin:
        p = (v - emin) / (emax - emin)
        if p > 1:
            p, hors = 1.0, True
        if p < 0:
            p = 0.0
        position = round(p, 4)
    return {
        "disponible": True,
        "valeur_m3s": v,
        "palier": _palier(v, cfg),
        "source": d["source"],
        "horodatage": d["horodatage"],
        "echelle": {
            "min_m3s": emin,
            "max_m3s": emax,
            "position": position,
            "hors_echelle": hors,
            "seuil_tranquille_m3s": nav.get("seuil_tranquille_m3s"),
            "seuil_fort_m3s": nav.get("seuil_fort_m3s"),
        },
        "navigation": {"niveau": _nav(v, nav), "note": nav.get("note")},
        "tendance": tend,
        "reperes": {
            "mediane_m3s": cfg.get("mediane_m3s"),
            "module_m3s": cfg.get("module_m3s"),
            "min_connu_m3s": cfg.get("min_connu_m3s"),
            "max_connu_m3s": cfg.get("max_connu_m3s"),
        },
    }


def _palier(v, cfg):
    seuil = cfg.get("seuil_vigilance_m3s") or cfg.get("qix2_m3s")
    mediane = cfg.get("mediane_m3s")
    if seuil and v >= seuil:
        return "eleve"
    if mediane is not None and v < mediane:
        return "faible"
    return "ok"


def _nav(v, nav):
    st = nav.get("seuil_tranquille_m3s")
    sf = nav.get("seuil_fort_m3s")
    if st is None or sf is None:
        return None
    if v <= st:
        return "tranquille"
    if v >= sf:
        return "fort"
    return "moyen"


def _meteo(site):
    m = openmeteo.meteo(site["lat"], site["lon"])
    m["disponible"] = True
    return m


def _webcam(site):
    cfg = site["webcam"]
    snap = webcam.snapshot(cfg["page_url"])
    base = {"nom": cfg.get("nom"), "page_url": cfg["page_url"]}
    if not snap:
        base["disponible"] = False
        return base
    base["disponible"] = True
    base["image_url"] = snap["image_url"]
    base["horodatage"] = snap.get("horodatage")
    return base


def _danger(debit, meteo):
    messages = []
    if debit.get("disponible") and debit.get("palier") == "eleve":
        messages.append(f"Débit Nive élevé : {debit.get('valeur_m3s')} m³/s")
    if meteo and meteo.get("disponible"):
        heure = _orage_proche(meteo.get("evolution_horaire", []))
        if meteo.get("orage"):
            messages.append("Orage en cours")
        elif heure:
            messages.append(f"Orage prévu vers {heure}")
    return {"actif": len(messages) > 0, "messages": messages}


def _orage_proche(evolution):
    maintenant = datetime.now(PARIS)
    for p in evolution:
        if not p.get("orage"):
            continue
        t = datetime.fromisoformat(p["heure_locale"])
        if t.tzinfo is None:  # heures Open-Meteo en local naïf -> on les rend tz-aware
            t = t.replace(tzinfo=PARIS)
        delta = (t - maintenant).total_seconds()
        if 0 <= delta <= 6 * 3600:
            return t.strftime("%Hh%M")
    return None
