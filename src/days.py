"""Dates and times in the user's time zone, and the compact views of meals, water and days."""
import datetime as dt
import re

import config
import db

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
TIME = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class NutritionError(Exception):
    """A refusal with a message for the agent (unknown id, bad time, ...)."""


def local(when: dt.datetime) -> dt.datetime:
    """A stored timestamp in the user's time zone."""
    return when.astimezone(config.TIMEZONE)


def now() -> dt.datetime:
    """The current time in the user's time zone."""
    return dt.datetime.now(config.TIMEZONE)


def today() -> dt.date:
    """Today in the user's time zone."""
    return now().date()


def moment(date: dt.date | None, time: str | None) -> dt.datetime:
    """The point in time of date + 'HH:MM' in the user's time zone. Missing date = today,
    missing time = now (on another day: 12:00)."""
    day = date or today()
    if time is None:
        current = now()
        return current if day == current.date() else dt.datetime.combine(
            day, dt.time(12, 0), config.TIMEZONE)
    match = TIME.match(time.strip())
    if not match:
        raise NutritionError(f"'{time}' is not a time: use HH:MM, e.g. '07:30'.")
    return dt.datetime.combine(day, dt.time(int(match[1]), int(match[2])), config.TIMEZONE)


def meal_type_at(when: dt.datetime) -> str:
    """The usual meal type for a time of day."""
    minutes = when.hour * 60 + when.minute
    if 5 * 60 <= minutes < 10 * 60 + 30:
        return "breakfast"
    if 11 * 60 <= minutes < 14 * 60 + 30:
        return "lunch"
    if 17 * 60 + 30 <= minutes < 21 * 60 + 30:
        return "dinner"
    return "snack"


def date_range(date: dt.date | None, end_date: dt.date | None) -> tuple[dt.date, dt.date]:
    """first..last from the date parameters: missing date = today, missing end_date = date."""
    first = date or today()
    last = end_date or first
    if last < first:
        raise NutritionError(f"end_date {last} is before date {first}.")
    if (last - first).days > 366:
        raise NutritionError("At most 366 days at once.")
    return first, last


def _number(value):
    """Postgres numeric → int when whole, else float with one decimal."""
    value = float(value)
    return int(value) if value.is_integer() else round(value, 1)


def meal_view(row: dict) -> dict:
    """Compact view of a meal; empty fields are left out."""
    when = local(row["eaten_at"])
    out = {"meal_id": row["id"], "date": when.date().isoformat(), "time": f"{when:%H:%M}",
           "meal_type": row["meal_type"], "name": row["name"], "components": row["components"]}
    out.update({v: _number(row[v]) for v in db.MEAL_VALUES if row[v] is not None})
    out.update(estimated=row["estimated"] or None, notes=row["notes"])
    return {k: v for k, v in out.items() if v is not None}


def water_view(row: dict) -> dict:
    """Compact view of a water entry."""
    when = local(row["drunk_at"])
    out = {"water_id": row["id"], "date": when.date().isoformat(), "time": f"{when:%H:%M}",
           "ml": row["ml"], "notes": row["notes"]}
    return {k: v for k, v in out.items() if v is not None}


def totals_view(day: dict | None) -> dict:
    """The summed values of a day (zeros for a day without entries)."""
    day = day or {}
    out = {v: _number(day.get(v) or 0) for v in ("kcal", "protein_g", "carbs_g", "fat_g")}
    out.update({v: _number(day[v]) for v in ("fiber_g", "sugar_g", "alcohol_g", "caffeine_mg")
                if day.get(v) is not None})
    out["water_ml"] = day.get("water_ml", 0)
    return out


def against_goals(totals: dict, goals: dict) -> dict:
    """For every goal that is set: goal, value so far and what is left (negative = over)."""
    out = {}
    for name, goal in goals.items():
        if goal is not None:
            value = totals.get(name, 0)
            out[name] = {"goal": _number(goal), "so_far": value,
                         "left": _number(float(goal) - value)}
    return out


def day_view(day: dt.date, totals: dict | None, goals: dict) -> dict:
    """One day: date, weekday, number of meals, totals and the comparison with the goals."""
    values = totals_view(totals)
    out = {"date": day.isoformat(), "weekday": WEEKDAYS[day.weekday()],
           "meals": (totals or {}).get("meals", 0), "total": values}
    if (totals or {}).get("estimated"):
        out["contains_estimates"] = True
    progress = against_goals(values, goals)
    if progress:
        out["goals"] = progress
    return out
