import requests

URL = "https://flood-api.open-meteo.com/v1/flood"


def tendance(lat, lon):
    r = requests.get(URL, params={"latitude": lat, "longitude": lon, "daily": "river_discharge", "forecast_days": 7}, timeout=25)
    r.raise_for_status()
    vals = [x for x in r.json().get("daily", {}).get("river_discharge", []) if x is not None]
    if len(vals) < 2 or vals[0] <= 0:
        return None
    var = (vals[-1] - vals[0]) / vals[0]
    if var > 0.15:
        sens = "hausse"
    elif var < -0.15:
        sens = "baisse"
    else:
        sens = "stable"
    return {"sens": sens, "variation_pct": round(var * 100)}
