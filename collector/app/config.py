import json
from pathlib import Path

SITES_DIR = Path(__file__).resolve().parent.parent / "sites"


def charger_site(site_id):
    chemin = SITES_DIR / f"{site_id}.json"
    if not chemin.exists():
        raise FileNotFoundError(f"site inconnu: {site_id}")
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def lister_sites():
    return [p.stem for p in SITES_DIR.glob("*.json")]
