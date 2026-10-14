#!/bin/bash
# One-off (2026-10): copy the data of the old stack (container nutrition-mcp: upstream
# nutrition-mcp + mcp-food in one Postgres) into nutrition-db.
#   meals, water, goals  → schema nutrition (body weight is dropped: it comes from Garmin)
#   food.*               → schema food (data only; the schema comes from mcp-food's schema.sql)
# Run from the repo root after `docker compose up -d` in db/; refuses to run twice.
set -euo pipefail
OLD=(sudo -n docker exec -i -u postgres nutrition-mcp psql -v ON_ERROR_STOP=1 -q -d postgres)
NEW=(sudo -n docker exec -i nutrition-db psql -v ON_ERROR_STOP=1 -q -U nutrition -d nutrition)
FOOD_SCHEMA=${FOOD_SCHEMA:-../mcp-food/src/schema.sql}

"${NEW[@]}" < src/schema.sql
"${NEW[@]}" < "$FOOD_SCHEMA"
if [[ $("${NEW[@]}" -Atc "select (select count(*) from nutrition.meals)
                              + (select count(*) from food.items)") != 0 ]]; then
  echo "nutrition-db already contains data - nothing done." >&2; exit 1
fi

"${OLD[@]}" -c "\copy (select logged_at, meal_type, description, coalesce(calories, 0),
    coalesce(protein_g, 0), coalesce(carbs_g, 0), coalesce(fat_g, 0), fiber_g, sugar_g,
    alcohol_g, caffeine_mg, description ilike '%geschätzt%', notes from meals
    order by logged_at) to stdout csv" |
  "${NEW[@]}" -c "\copy nutrition.meals (eaten_at, meal_type, name, kcal, protein_g, carbs_g,
    fat_g, fiber_g, sugar_g, alcohol_g, caffeine_mg, estimated, notes) from stdin csv"

"${OLD[@]}" -c "\copy (select logged_at, amount_ml, notes from water_log order by logged_at)
    to stdout csv" |
  "${NEW[@]}" -c "\copy nutrition.water (drunk_at, ml, notes) from stdin csv"

"${OLD[@]}" -c "\copy (select daily_calories, daily_protein_g, daily_carbs_g, daily_fat_g,
    daily_fiber_g, daily_sugar_g, daily_water_ml from nutrition_goals) to stdout csv" |
  "${NEW[@]}" -c "\copy nutrition.goals (kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g,
    water_ml) from stdin csv"

sudo -n docker exec -u postgres nutrition-mcp pg_dump -d postgres -n food --data-only \
    --no-owner --no-privileges |
  "${NEW[@]}"

"${NEW[@]}" -Atc "select 'meals ' || count(*) from nutrition.meals
                  union all select 'water ' || count(*) from nutrition.water
                  union all select 'goals ' || count(*) from nutrition.goals
                  union all select 'food.items ' || count(*) from food.items
                  union all select 'food.recipes ' || count(*) from food.recipes
                  union all select 'food.recipe_items ' || count(*) from food.recipe_items"
