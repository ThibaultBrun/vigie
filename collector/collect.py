import json
from pathlib import Path
from app.build import construire
from app.config import lister_sites

SORTIE = Path(__file__).resolve().parent.parent / "web" / "public" / "data"


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    for site_id in lister_sites():
        donnees = construire(site_id)
        chemin = SORTIE / f"{site_id}.json"
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        print(f"ecrit {chemin}")


if __name__ == "__main__":
    main()
