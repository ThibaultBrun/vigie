import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

PARIS = ZoneInfo("Europe/Paris")


def snapshot(page_url):
    r = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (vigie)"})
    r.raise_for_status()
    m = re.search(r'og:image"[^>]*content="([^"]+)"', r.text)
    if not m:
        return None
    image_url = m.group(1)
    horodatage = None
    ts = re.search(r"media_(\d{10})", image_url)
    if ts:
        horodatage = datetime.fromtimestamp(int(ts.group(1)), PARIS).isoformat()
    return {"image_url": image_url, "horodatage": horodatage}
