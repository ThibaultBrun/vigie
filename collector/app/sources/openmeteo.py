import requests

URL = "https://api.open-meteo.com/v1/forecast"
DIRS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def _dir(deg):
    if deg is None:
        return None
    return DIRS[int((deg % 360) / 22.5 + 0.5) % 16]


def meteo(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover",
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m,cloud_cover",
        "daily": "sunset",
        "timezone": "Europe/Paris",
        "wind_speed_unit": "kmh",
        "forecast_days": 3,
    }
    r = requests.get(URL, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()
    c = d.get("current", {})
    daily = d.get("daily", {})
    hourly = d.get("hourly", {})
    sunset = daily.get("sunset", [None])
    return {
        "vent_kmh": c.get("wind_speed_10m"),
        "vent_dir": _dir(c.get("wind_direction_10m")),
        "vent_dir_deg": c.get("wind_direction_10m"),
        "rafales_kmh": c.get("wind_gusts_10m"),
        "temp_c": c.get("temperature_2m"),
        "cloud_cover_pct": c.get("cloud_cover"),
        "coucher_soleil_local": sunset[0] if sunset else None,
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
    out = []
    for i in range(len(heures)):
        out.append({
            "heure_locale": heures[i],
            "vent_kmh": vent[i] if i < len(vent) else None,
            "rafales_kmh": rafales[i] if i < len(rafales) else None,
            "vent_dir": _dir(direction[i]) if i < len(direction) else None,
            "temp_c": temp[i] if i < len(temp) else None,
            "cloud_cover_pct": nuages[i] if i < len(nuages) else None,
        })
    return out
