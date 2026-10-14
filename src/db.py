"""Postgres access for the schema "nutrition": meals, water and the daily goals."""
from datetime import date, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

import config

MEAL_VALUES = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "alcohol_g",
               "caffeine_mg")
MEAL_FIELDS = ("eaten_at", "meal_type", "name", "components", *MEAL_VALUES, "estimated", "notes")
GOAL_FIELDS = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "water_ml")
SCHEMA = Path(__file__).with_name("schema.sql")

_CONN: dict = {}


def conn() -> psycopg.Connection:
    """The process-wide connection (autocommit), reopened when it was closed."""
    current = _CONN.get("conn")
    if current is None or current.closed:
        current = _CONN["conn"] = psycopg.connect(config.DATABASE_URL, row_factory=dict_row,
                                                  autocommit=True)
    return current


def init_schema() -> None:
    """Create the schema and its tables if they do not exist yet."""
    conn().execute(SCHEMA.read_text(encoding="utf-8"))


def _local_day() -> sql.Composable:
    """SQL for the local calendar day of a timestamp column named ts."""
    return sql.SQL("(ts at time zone {})::date").format(sql.Literal(config.TIMEZONE.key))


# --- meals ---

def insert_meal(meal: dict) -> dict:
    """Store a meal (keys from MEAL_FIELDS); returns the stored row."""
    cols = [c for c in MEAL_FIELDS if c in meal]
    query = sql.SQL("insert into nutrition.meals ({}) values ({}) returning *").format(
        sql.SQL(", ").join(map(sql.Identifier, cols)),
        sql.SQL(", ").join(sql.Placeholder(c) for c in cols))
    return conn().execute(query, meal).fetchone()


def get_meal(meal_id: int) -> dict | None:
    """The meal with this id, or None."""
    return conn().execute("select * from nutrition.meals where id = %s", (meal_id,)).fetchone()


def update_meal(meal_id: int, changes: dict) -> dict | None:
    """Change the given fields of a meal; returns the updated row (None: no such meal)."""
    query = sql.SQL("update nutrition.meals set {}, updated_at = now() where id = {} "
                    "returning *").format(
        sql.SQL(", ").join(sql.SQL("{} = {}").format(sql.Identifier(c), sql.Placeholder(c))
                           for c in changes),
        sql.Literal(meal_id))
    return conn().execute(query, changes).fetchone()


def delete_meal(meal_id: int) -> None:
    """Delete a meal."""
    conn().execute("delete from nutrition.meals where id = %s", (meal_id,))


def meals_between(first: date, last: date) -> list[dict]:
    """The meals of the local days first..last (inclusive), in time order."""
    query = sql.SQL("select *, {day} as day from (select *, eaten_at as ts from nutrition.meals) m "
                    "where {day} between %s and %s order by eaten_at").format(day=_local_day())
    return conn().execute(query, (first, last)).fetchall()


def search_meals(words: list[str], limit: int) -> list[dict]:
    """The latest meals whose name, components or notes contain every word."""
    text = "lower(name || ' ' || coalesce(components, '') || ' ' || coalesce(notes, ''))"
    where = " and ".join(f"{text} like %s" for _ in words)
    return conn().execute(
        f"select * from nutrition.meals where {where} order by eaten_at desc limit %s",
        [*(f"%{w.lower()}%" for w in words), limit]).fetchall()


def day_totals(first: date, last: date) -> dict[date, dict]:
    """Per local day first..last: the sums of the meal values, the number of meals and the
    water in ml. Days without any entry are missing."""
    sums = ", ".join(f"sum({v}) as {v}" for v in MEAL_VALUES)
    meals = conn().execute(
        sql.SQL("select {day} as day, count(*) as meals, bool_or(estimated) as estimated, "
                + sums + " from (select *, eaten_at as ts from nutrition.meals) m "
                "where {day} between %s and %s group by 1").format(day=_local_day()),
        (first, last)).fetchall()
    water = conn().execute(
        sql.SQL("select {day} as day, sum(ml) as water_ml "
                "from (select *, drunk_at as ts from nutrition.water) w "
                "where {day} between %s and %s group by 1").format(day=_local_day()),
        (first, last)).fetchall()
    days: dict[date, dict] = {}
    for row in meals:
        days[row.pop("day")] = row
    for row in water:
        days.setdefault(row["day"], {"meals": 0})["water_ml"] = int(row["water_ml"])
    return days


# --- water ---

def insert_water(drunk_at: datetime, ml: int, notes: str | None) -> dict:
    """Store a water entry; returns the stored row."""
    return conn().execute("insert into nutrition.water (drunk_at, ml, notes) values (%s, %s, %s) "
                          "returning *", (drunk_at, ml, notes)).fetchone()


def get_water(water_id: int) -> dict | None:
    """The water entry with this id, or None."""
    return conn().execute("select * from nutrition.water where id = %s", (water_id,)).fetchone()


def delete_water(water_id: int) -> None:
    """Delete a water entry."""
    conn().execute("delete from nutrition.water where id = %s", (water_id,))


def water_between(first: date, last: date) -> list[dict]:
    """The water entries of the local days first..last, in time order."""
    query = sql.SQL("select *, {day} as day from (select *, drunk_at as ts from nutrition.water) w "
                    "where {day} between %s and %s order by drunk_at").format(day=_local_day())
    return conn().execute(query, (first, last)).fetchall()


# --- goals ---

def get_goals() -> dict:
    """The daily goals (every field None when none are set)."""
    row = conn().execute("select * from nutrition.goals where id = 1").fetchone()
    return {f: (row or {}).get(f) for f in GOAL_FIELDS}


def set_goals(changes: dict) -> dict:
    """Set the given goal fields (None clears one); returns all goals."""
    cols = list(changes)
    query = sql.SQL("insert into nutrition.goals (id, {cols}) values (1, {vals}) "
                    "on conflict (id) do update set {sets}, updated_at = now()").format(
        cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
        vals=sql.SQL(", ").join(sql.Placeholder(c) for c in cols),
        sets=sql.SQL(", ").join(sql.SQL("{0} = excluded.{0}").format(sql.Identifier(c))
                                for c in cols))
    conn().execute(query, changes)
    return get_goals()
