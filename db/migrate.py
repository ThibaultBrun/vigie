#!/usr/bin/env python3
"""Applique les migrations SQL versionnées de db/migrations/ (idempotent).

Chaque fichier *.sql est joué une seule fois, dans l'ordre alphabétique, et
enregistré dans la table schema_migrations. Piloté par le dépôt : ajouter une
migration = déposer un nouveau fichier 000N_xxx.sql et relancer ce script.

Usage : DATABASE_URL=postgresql://... python db/migrate.py
"""
import os
import pathlib
import sys

import psycopg

HERE = pathlib.Path(__file__).resolve().parent
MIGRATIONS = HERE / "migrations"


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL manquant (voir db/.env)")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "create table if not exists schema_migrations ("
                "version text primary key, applied_at timestamptz not null default now())"
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("select version from schema_migrations")
            deja = {r[0] for r in cur.fetchall()}
        applique = 0
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in deja:
                continue
            with conn.cursor() as cur:
                cur.execute(f.read_text(encoding="utf-8"))
                cur.execute("insert into schema_migrations (version) values (%s)", (f.name,))
            conn.commit()
            print(f"appliqué {f.name}")
            applique += 1
        print(f"migrations à jour ({applique} nouvelle(s))")


if __name__ == "__main__":
    main()
