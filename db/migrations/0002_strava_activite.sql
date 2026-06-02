-- Activités Strava (sorties pirogue) pour l'analyse renverse / effort.
create table if not exists strava_activite (
  id             bigint primary key,            -- id Strava de l'activité
  athlete_id     bigint,
  type           text,                          -- Canoeing / Kayaking / Rowing / StandUpPaddling…
  nom            text,
  start_date     timestamptz not null,          -- début (UTC)
  distance_m     double precision,
  moving_time_s  integer,
  elapsed_time_s integer,
  average_speed  double precision,              -- m/s
  polyline       text,                          -- tracé encodé (summary polyline)
  raw            jsonb,
  importe_le     timestamptz not null default now()
);
create index if not exists strava_activite_start_idx on strava_activite (start_date);
