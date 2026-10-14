"""Evaluation tools: days against the goals, and averages over the last weeks."""
import datetime as dt
from typing import Annotated, Literal

import db
import days
from tools._shared import Date, EndDate, doc, nutrition_tool


def day_status(day: dt.date) -> dict:
    """One day's totals against the goals (what meal_log and water_log return)."""
    return days.day_view(day, db.day_totals(day, day).get(day), db.get_goals())


@nutrition_tool
def day_summary(date: Date = None, end_date: EndDate = None) -> list[dict]:
    """Totals of one day or of every day of a range: kcal, protein, carbs, fat (and fibre,
    sugar, alcohol, caffeine when recorded), water, number of meals - and for every goal that
    is set: goal, so far, left (negative = over the goal). The meals themselves: meal_list."""
    first, last = days.date_range(date, end_date)
    totals, goals = db.day_totals(first, last), db.get_goals()
    return [days.day_view(first + dt.timedelta(n), totals.get(first + dt.timedelta(n)), goals)
            for n in range((last - first).days + 1)]


@nutrition_tool
def trend_get(
    days_back: Annotated[Literal[7, 14, 30], doc("Length of the window in days, ending "
                                                 "yesterday (today is still incomplete).")] = 7,
) -> dict:
    """Averages over the last 7, 14 or 30 complete days (ending yesterday), counted over the
    days with at least one logged meal; with the number of such days, the goals and the
    lowest/highest kcal day. For one day or a short range use day_summary."""
    last = days.today() - dt.timedelta(days=1)
    first = last - dt.timedelta(days=days_back - 1)
    logged = {d: t for d, t in db.day_totals(first, last).items() if t.get("meals")}
    out: dict = {"from": first.isoformat(), "to": last.isoformat(), "days": days_back,
                 "days_with_meals": len(logged)}
    if not logged:
        return out
    views = {d: days.totals_view(t) for d, t in logged.items()}
    names = sorted({k for v in views.values() for k in v} - {"water_ml"},
                   key=list(db.MEAL_VALUES).index)
    out["average_per_day"] = {n: round(sum(v.get(n, 0) for v in views.values()) / len(views), 1)
                              for n in names}
    water = [t.get("water_ml", 0) for t in db.day_totals(first, last).values()]
    out["average_water_ml"] = round(sum(water) / days_back)
    goals = {k: float(v) for k, v in db.get_goals().items() if v is not None}
    if goals:
        out["goals"] = goals
    low, high = (min(views, key=lambda d: views[d]["kcal"]),
                 max(views, key=lambda d: views[d]["kcal"]))
    out["lowest_kcal_day"] = {"date": low.isoformat(), "kcal": views[low]["kcal"]}
    out["highest_kcal_day"] = {"date": high.isoformat(), "kcal": views[high]["kcal"]}
    return out
