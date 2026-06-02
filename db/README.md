# Base de données Vigie

Postgres dédié (instance minimale, isolée), piloté par le dépôt.

## Démarrer

```bash
cd db
cp .env.example .env            # puis renseigner POSTGRES_PASSWORD et DATABASE_URL
docker compose up -d            # Postgres sur 127.0.0.1:5433
```

## Migrations

Migrations SQL versionnées dans `db/migrations/` (jouées une fois, dans l'ordre).
Ajouter une migration = déposer `000N_description.sql` puis relancer :

```bash
pip install -r requirements.txt           # psycopg
export $(grep -v '^#' .env | xargs)       # charge DATABASE_URL
python migrate.py
```

## Schéma (0001)

- `station` — stations Hub'Eau suivies (Convergent, Pont Blanc, Cambo).
- `observation` — séries temporelles brutes (H en m, Q en m³/s), PK (station, ts).
- `renverse_observation` — relevés terrain de renverse de courant (calibration).

Le snapshot live de l'appli reste en JSON statique ; la base sert l'historique et l'analyse.
