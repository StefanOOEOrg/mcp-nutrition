create schema if not exists nutrition;

create table if not exists nutrition.meals (
  id          serial primary key,
  eaten_at    timestamptz not null,
  meal_type   text not null check (meal_type in ('breakfast', 'lunch', 'dinner', 'snack', 'drink')),
  name        text not null,
  components  text,
  kcal        numeric not null check (kcal >= 0),
  protein_g   numeric not null check (protein_g >= 0),
  carbs_g     numeric not null check (carbs_g >= 0),
  fat_g       numeric not null check (fat_g >= 0),
  fiber_g     numeric check (fiber_g >= 0),
  sugar_g     numeric check (sugar_g >= 0),
  alcohol_g   numeric check (alcohol_g >= 0),
  caffeine_mg numeric check (caffeine_mg >= 0),
  estimated   boolean not null default false,
  notes       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists meals_eaten_at on nutrition.meals (eaten_at);

create table if not exists nutrition.water (
  id         serial primary key,
  drunk_at   timestamptz not null,
  ml         integer not null check (ml > 0),
  notes      text,
  created_at timestamptz not null default now()
);
create index if not exists water_drunk_at on nutrition.water (drunk_at);

-- one row (id = 1): the daily targets
create table if not exists nutrition.goals (
  id         integer primary key default 1 check (id = 1),
  kcal       numeric,
  protein_g  numeric,
  carbs_g    numeric,
  fat_g      numeric,
  fiber_g    numeric,
  sugar_g    numeric,
  water_ml   integer,
  updated_at timestamptz not null default now()
);
