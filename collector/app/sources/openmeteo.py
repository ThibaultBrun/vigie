import time

import requests

URL = "https://api.open-meteo.com/v1/forecast"
DIRS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def _dir(deg):
    if deg is None:
        return None
    return DIRS[int((deg % 360) / 22.5 + 0.5) % 16]


def _orage(code):
    return code in (95, 96, 99)


def _ciel(code):
    if code is None:
        return None
    if code == 0:
        return "ciel clair"
    if code in (1, 2, 3):
        return "nuageux"
    if code in (45, 48):
        return "brouillard"
    if code in (51, 53, 55, 56, 57):
        return "bruine"
    if code in (61, 63, 65, 66, 67):
        return "pluie"
    if code in (71, 73, 75, 77, 85, 86):
        return "neige"
    if code in (80, 81, 82):
        return "averses"
    if code in (95, 96, 99):
        return "orage"
    return None


def meteo(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,precipitation,weather_code",
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m,cloud_cover,precipitation,precipitation_probability,weather_code",
        "daily": "sunset",
        "timezone": "Europe/Paris",
        "wind_speed_unit": "kmh",
        "forecast_days": 7,
    }
    derniere = None
    for _ in range(3):
        try:
            r = requests.get(URL, params=params, timeout=(10, 30))
            r.raise_for_status()
            d = r.json()
            break
        except requests.RequestException as e:
            derniere = e
            time.sleep(2)
    else:
        raise derniere
    c = d.get("current", {})
    daily = d.get("daily", {})
    hourly = d.get("hourly", {})
    sunset = daily.get("sunset", [None])
    sdates = daily.get("time", [])
    couchers = [{"date": sdates[i], "heure": sunset[i]} for i in range(min(len(sdates), len(sunset)))]
    return {
        "vent_kmh": c.get("wind_speed_10m"),
        "vent_dir": _dir(c.get("wind_direction_10m")),
        "vent_dir_deg": c.get("wind_direction_10m"),
        "rafales_kmh": c.get("wind_gusts_10m"),
        "temp_c": c.get("temperature_2m"),
        "cloud_cover_pct": c.get("cloud_cover"),
        "pluie_mm": c.get("precipitation"),
        "ciel": _ciel(c.get("weather_code")),
        "orage": _orage(c.get("weather_code")),
        "coucher_soleil_local": sunset[0] if sunset else None,
        "coucher_soleil_jours": couchers,
        "horodatage": c.get("time"),
        "evolution_horaire": _evolution(hourly),
    }


def _evolution(hourly):
    heures = hourly.get("time", [])
    vent = hourly.get("wind_speed_10m", [])
    rafales = hourly.get("wind_gusts_10m", [])
    direction = hourly.get("wind_direction_10m", [])
    temp = hourly.get("temperature_2m", [])
    nuages = hourly.get("cloud_cover", [])
    pluie = hourly.get("precipitation", [])
    proba = hourly.get("precipitation_probability", [])
    codes = hourly.get("weather_code", [])
    out = []
    for i in range(len(heures)):
        code = codes[i] if i < len(codes) else None
        out.append({
            "heure_locale": heures[i],
            "vent_kmh": vent[i] if i < len(vent) else None,
            "rafales_kmh": rafales[i] if i < len(rafales) else None,
            "vent_dir": _dir(direction[i]) if i < len(direction) else None,
            "temp_c": temp[i] if i < len(temp) else None,
            "cloud_cover_pct": nuages[i] if i < len(nuages) else None,
            "pluie_mm": pluie[i] if i < len(pluie) else None,
            "pluie_proba": proba[i] if i < len(proba) else None,
            "ciel": _ciel(code),
            "orage": _orage(code),
        })
    return out
