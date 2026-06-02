-- Schéma initial Vigie : stations, séries temporelles, relevés de renverse.

-- Stations hydrométriques suivies (Hub'Eau)
create table if not exists station (
  code      text primary key,
  nom       text not null,
  riviere   text,
  latitude  double precision,
  longitude double precision
);

insert into station (code, nom, riviere, latitude, longitude) values
  ('Q935001001', 'Convergent (embouchure Adour)', 'Adour', 43.5274, -1.5148),
  ('Q935251001', 'Pont Blanc', 'Nive', 43.4778, -1.4724),
  ('Q931251001', 'Cambo-les-Bains', 'Nive', 43.358, -1.403)
on conflict (code) do nothing;

-- Séries temporelles brutes. Unités SI : H en mètres, Q en m³/s.
create table if not exists observation (
  station_code text not null references station (code),
  grandeur     char(1) not null check (grandeur in ('H', 'Q')),
  ts           timestamptz not null,
  valeur       double precision not null,
  primary key (station_code, ts)
);
create index if not exists observation_ts_idx on observation (ts);

-- Relevés terrain de renverse de courant (calibration du modèle dη/dt)
create table if not exists renverse_observation (
  id          bigint generated always as identity primary key,
  site        text not null default 'bayonne-nive',
  observe_le  timestamptz not null,                 -- heure réelle constatée de la renverse
  sens        text not null check (sens in ('flot→jusant', 'jusant→flot')),
  debit_m3s   double precision,                      -- contexte (peut être rempli depuis les données)
  auteur      text,
  commentaire text,
  cree_le     timestamptz not null default now()
);
