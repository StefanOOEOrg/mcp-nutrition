# mcp-nutrition

[![CI](https://github.com/StefanOOEOrg/mcp-nutrition/actions/workflows/ci.yml/badge.svg)](https://github.com/StefanOOEOrg/mcp-nutrition/actions/workflows/ci.yml)
[![M8ven Score](https://m8ven.ai/badge/mcp/stefanooeorg-mcp-nutrition-18sq6o?v=2533f3d1074f60a1a237ee065b9dd047)](https://m8ven.ai/mcp/stefanooeorg-mcp-nutrition-18sq6o?s=readme)

MCP server (stdio) for a **food diary** - meals with their nutrition values, water, daily goals
and the evaluation of days and weeks. The values of
a meal come from [mcp-food](https://github.com/StefanOOEOrg/mcp-food) (`food_nutrition`),
whose `total` uses the same field names as `meal_log`.

Replaces the self-hosted upstream [nutrition-mcp](https://github.com/akutishevsky/nutrition-mcp)
(TypeScript, OAuth, 36 tools; until 2026-10): 12 tools with unambiguous names, no OAuth, plain
Postgres. Body weight is not part of it - it comes from Garmin (mcp-garmin).

- [Requirements](#requirements)
- [Database](#database)
- [Setup](#setup)
- [Project structure](#project-structure)
- [Development](#development)
- [Scope / Limitations](#scope--limitations)
- [Tool reference](#tool-reference)

## Requirements

- **Python 3.11 or newer** — the pinned dependencies require it; the CI runs 3.11 and 3.14.
- **Postgres 17** with the `nutrition` schema (this server) and the `food` schema (mcp-food). The `db/`
  folder ships the container, the init script and a backup script.
- Nothing else: no account, no API key, no open port — an MCP server over stdio for a local client.

## Database

`db/` holds the Postgres container `nutrition-db` (127.0.0.1:5433) for both servers:
schema `nutrition` (this server) and `food` (mcp-food), role and database `nutrition`.

```bash
cd db && cp .env.example .env    # fill both passwords
sudo docker compose up -d        # first start creates role + database (init/)
```

Backup: `db/backup.sh` (pg_dump of the whole database, 14 days) runs daily at 03:15 via the
systemd user timer `nutrition-backup.timer` of ss → `~/backups/nutrition/`.
Restore: `sudo docker exec -i nutrition-db pg_restore -U postgres -d nutrition --clean < <dump>`.

`scripts/migrate_from_nutrition_mcp.sh` copied the data of the old container `nutrition-mcp`
once (2026-10-14). Kept: goals, 7,323 foods, 17 recipes; the copied meal and water logs were deleted afterwards (the diary starts empty).

## Setup

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
echo 'NUTRITION_DATABASE_URL=postgresql://nutrition:<password>@127.0.0.1:5433/nutrition' > .env
```

| Variable | Meaning |
|---|---|
| `NUTRITION_DATABASE_URL` | libpq URL of the database |
| `NUTRITION_TIMEZONE` | the user's time zone for "today", dates and times (default `Europe/Vienna`) |
| `LOG_LEVEL` | default `INFO` |

Install it with its own venv and `.env` and add it to Hermes' `config.yaml`:

```yaml
mcp_servers:
  mcp-nutrition:
    command: /path/to/mcp-nutrition/.venv/bin/python
    args: [/path/to/mcp-nutrition/src/main.py]
```

## Project structure

```
mcp-nutrition/
├── src/
│   ├── config.py            # NUTRITION_* / LOG_LEVEL from the environment
│   ├── db.py                # connection handling + schema init
│   ├── days.py              # day and week boundaries in the configured time zone
│   ├── main.py              # entry point (stdio)
│   ├── mcp_server.py        # composition root: server + tools
│   ├── schema.sql           # the `nutrition` schema
│   ├── server_instance.py   # the shared MCP server instance
│   └── tools/               # meal, water, day, goals + _shared helpers
├── tests/                   # run against a throwaway Postgres (TEST_DATABASE_URL)
├── db/                      # docker-compose, init script, backup.sh, db/.env.example
├── scripts/                 # one-off migration + tool_reference.py
├── .github/workflows/ci.yml # pytest against a Postgres service + pylint, on 3.11 and 3.14
├── .env.example             # copy to .env
├── .pylintrc
├── pytest.ini
├── requirements.txt / requirements-dev.txt
├── LICENSE
└── README.md
```

## Development

```bash
venv/bin/pip install -r requirements-dev.txt
sudo docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test \
    -p 127.0.0.1:55432:5432 --tmpfs /var/lib/postgresql/data postgres:17.11
venv/bin/python -m pytest          # TEST_DATABASE_URL overrides the test database
venv/bin/pylint src tests scripts  # must stay at 10/10
venv/bin/python scripts/tool_reference.py   # regenerate the tool reference below
```

Every test drops and recreates the schema - never point `TEST_DATABASE_URL` at the real
database.

## Scope / Limitations

- A single-user tool, not a service: it runs locally over stdio — no port of its own, no
  authentication, no multi-user support.
- It needs the Postgres container; without it every tool fails with a readable error, and the tests
  skip locally (in CI they fail instead, via `TEST_REQUIRE_DB=1`).
- Nutrition values come from mcp-food; this server stores and aggregates them, it does not carry the
  food database itself.
- The database holds personal data (meals, water, goals). Back it up (`db/backup.sh`) and keep `.env`
  out of the repo.
- The schema is created from `src/schema.sql`; changes there are one-way — there is no migration
  framework.

## Tool reference

<!-- tool-reference:start -->

### Meal

#### `meal_log`

Record one meal the user reported, with the total values of the meal. Required: name, kcal, protein_g, carbs_g and fat_g - take all four numbers from the `total` of food_nutrition (and fiber_g, sugar_g too when it has them). Returns the stored meal (with meal_id) and the totals of that day against the goals - enough to report the day's status without another call. To change a meal later use meal_update, not a second meal_log.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | text | yes | Short name of the meal, e.g. 'Overnight Oats + Kaffee'. |
| `kcal` | number | yes | Required. Energy in kcal of the whole meal ('kcal' of food_nutrition's total). |
| `protein_g` | number | yes | Required. Protein in g of the whole meal ('protein_g' of the total). |
| `carbs_g` | number | yes | Required. Carbohydrates in g of the whole meal ('carbs_g' of the total; 0 if there are none). |
| `fat_g` | number | yes | Required. Fat in g of the whole meal ('fat_g' of the total; 0 if there is none). |
| `meal_type` | `breakfast` / `lunch` / `dinner` / `snack` / `drink` | no (default `none`) | Kind of meal. Default by time of day: before 10:30 breakfast, 11:00-14:30 lunch, 17:30-21:30 dinner, otherwise snack. 'drink' for drinks with energy (shake, juice, sports drink); plain water goes to water_log. |
| `date` | text | no (default `none`) | Day as 'YYYY-MM-DD' in the user's time zone; default today. |
| `time` | text | no (default `none`) | Time of day as 'HH:MM', e.g. '07:30'; default now (for another day than today: 12:00). |
| `components` | text | no (default `none`) | The single components with their amounts as ONE plain text (a string, not a list), e.g. 'Haferflocken 60 g, Skyr 150 g, Heidelbeeren 100 g'. Build it from the items of food_nutrition: '<name> <amount>' joined by ', '. |
| `fiber_g` | number | no (default `none`) | Fibre in g, if known. |
| `sugar_g` | number | no (default `none`) | Sugar in g, if known. |
| `alcohol_g` | number | no (default `none`) | Alcohol in g, if any. |
| `caffeine_mg` | number | no (default `none`) | Caffeine in mg, if any (coffee ~ 80-100 mg/cup). |
| `estimated` | yes/no | no (default `False`) | true if the values are estimated rather than taken from mcp-food. |
| `notes` | text | no (default `none`) | Free note, e.g. 'im Restaurant'. |

#### `meal_list`

The meals of one day (default today) or of a range of days, in time order, each with meal_id, date, time, meal_type, name, components and values. Totals: day_summary.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | text | no (default `none`) | Day as 'YYYY-MM-DD' in the user's time zone; default today. |
| `end_date` | text | no (default `none`) | Last day of a range as 'YYYY-MM-DD' (inclusive); default = date (one day only). |

#### `meal_search`

Find earlier meals by words, newest first - e.g. to log 'the same as last Tuesday' again with the same values.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | text | yes | Words that must all appear in the name, components or notes, e.g. 'oats' or 'pizza restaurant'. |
| `limit` | number | no (default `10`) | Maximum number of meals. |

#### `meal_update`

Correct a recorded meal: only the fields that are given change, everything else stays (to change the amount, give the new totals kcal, protein_g, carbs_g, fat_g). Returns the updated meal and the totals of its day.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `meal_id` | number | yes | meal_id of the meal, as meal_list, meal_search or meal_log return it. |
| `name` | text | no (default `none`) | New name. |
| `kcal` | number | no (default `none`) | New energy in kcal. |
| `protein_g` | number | no (default `none`) | New protein in g. |
| `carbs_g` | number | no (default `none`) | New carbohydrates in g. |
| `fat_g` | number | no (default `none`) | New fat in g. |
| `meal_type` | `breakfast` / `lunch` / `dinner` / `snack` / `drink` | no (default `none`) | New kind of meal. |
| `date` | text | no (default `none`) | Move the meal to this day ('YYYY-MM-DD'). |
| `time` | text | no (default `none`) | Move the meal to this time ('HH:MM'). |
| `components` | text | no (default `none`) | The single components with their amounts as ONE plain text (a string, not a list), e.g. 'Haferflocken 60 g, Skyr 150 g, Heidelbeeren 100 g'. Build it from the items of food_nutrition: '<name> <amount>' joined by ', '. |
| `fiber_g` | number | no (default `none`) | Fibre in g, if known. |
| `sugar_g` | number | no (default `none`) | Sugar in g, if known. |
| `alcohol_g` | number | no (default `none`) | Alcohol in g, if any. |
| `caffeine_mg` | number | no (default `none`) | Caffeine in mg, if any (coffee ~ 80-100 mg/cup). |
| `estimated` | yes/no | no (default `none`) | Mark the values as estimated (true) or not (false). |
| `notes` | text | no (default `none`) | Free note, e.g. 'im Restaurant'. |

#### `meal_delete`

Delete a recorded meal for good (there is no undo). Returns what was deleted and the totals of its day afterwards.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `meal_id` | number | yes | meal_id of the meal, as meal_list, meal_search or meal_log return it. |

### Water

#### `water_log`

Record water (or other drinks without energy: tea, sparkling water) the user drank. Drinks with energy go to meal_log (meal_type 'drink'); a drink logged there can also be counted here with its volume. Returns the entry (with water_id) and the totals of the day, including water so far against the water goal.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ml` | number | yes | Amount in millilitres, e.g. 500 (a glass ~ 250, a bottle 500-750, 1 l = 1000). |
| `date` | text | no (default `none`) | Day as 'YYYY-MM-DD' in the user's time zone; default today. |
| `time` | text | no (default `none`) | Time of day as 'HH:MM', e.g. '07:30'; default now (for another day than today: 12:00). |
| `notes` | text | no (default `none`) | Free note, e.g. 'mit Elektrolyten'. |

#### `water_list`

The water entries of one day (default today) with water_id and time, and their sum.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | text | no (default `none`) | Day as 'YYYY-MM-DD' in the user's time zone; default today. |

#### `water_delete`

Delete a water entry for good (there is no undo).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `water_id` | number | yes | water_id of the entry, as water_list or water_log return it. |

### Day

#### `day_summary`

Totals of one day or of every day of a range: kcal, protein, carbs, fat (and fibre, sugar, alcohol, caffeine when recorded), water, number of meals - and for every goal that is set: goal, so far, left (negative = over the goal). The meals themselves: meal_list.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | text | no (default `none`) | Day as 'YYYY-MM-DD' in the user's time zone; default today. |
| `end_date` | text | no (default `none`) | Last day of a range as 'YYYY-MM-DD' (inclusive); default = date (one day only). |

#### `trend_get`

Averages over the last 7, 14 or 30 complete days (ending yesterday), counted over the days with at least one logged meal; with the number of such days, the goals and the lowest/highest kcal day. For one day or a short range use day_summary.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `days_back` | `7` / `14` / `30` | no (default `7`) | Length of the window in days, ending yesterday (today is still incomplete). |

### Goals

#### `goals_get`

The user's daily goals; a goal that is not set is null.

#### `goals_set`

Change daily goals - only when the user asks for it. Only the given goals change; `clear` removes goals. Returns all goals afterwards.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `kcal` | number | no (default `none`) | Daily energy goal in kcal. |
| `protein_g` | number | no (default `none`) | Daily protein goal in g (a minimum). |
| `carbs_g` | number | no (default `none`) | Daily carbohydrate goal in g. |
| `fat_g` | number | no (default `none`) | Daily fat goal in g. |
| `fiber_g` | number | no (default `none`) | Daily fibre goal in g (a minimum). |
| `sugar_g` | number | no (default `none`) | Daily sugar limit in g. |
| `water_ml` | number | no (default `none`) | Daily water goal in ml. |
| `clear` | list | no (default `none`) | Names of goals to remove, e.g. ['carbs_g']. |

<!-- tool-reference:end -->

## License

[MIT](LICENSE)
