"""Water tools: record, list and delete what the user drank."""
from typing import Annotated

import db
import days
from days import NutritionError
from tools._shared import Date, Time, WaterId, doc, nutrition_tool
from tools.day import day_status


@nutrition_tool
def water_log(
    ml: Annotated[int, doc("Amount in millilitres, e.g. 500 (a glass ~ 250, a bottle 500-750, "
                           "1 l = 1000).")],
    date: Date = None,
    time: Time = None,
    notes: Annotated[str | None, doc("Free note, e.g. 'mit Elektrolyten'.")] = None,
) -> dict:
    """Record water (or other drinks without energy: tea, sparkling water) the user drank.
    Drinks with energy go to meal_log (meal_type 'drink'); a drink logged there can also be
    counted here with its volume. Returns the entry (with water_id) and the totals of the day,
    including water so far against the water goal."""
    if ml <= 0 or ml > 5000:
        raise NutritionError(f"{ml} ml is not plausible for one entry (1 to 5000 ml).")
    row = db.insert_water(days.moment(date, time), ml, notes)
    return {"logged": days.water_view(row), "day": day_status(days.local(row["drunk_at"]).date())}


@nutrition_tool
def water_list(date: Date = None) -> dict:
    """The water entries of one day (default today) with water_id and time, and their sum."""
    first, last = days.date_range(date, None)
    entries = [days.water_view(r) for r in db.water_between(first, last)]
    return {"date": first.isoformat(), "entries": entries,
            "total_ml": sum(e["ml"] for e in entries)}


@nutrition_tool
def water_delete(water_id: WaterId) -> dict:
    """Delete a water entry for good (there is no undo)."""
    row = db.get_water(water_id)
    if not row:
        raise NutritionError(f"There is no water entry with water_id {water_id}: water_list "
                             "shows the entries of a day.")
    db.delete_water(water_id)
    return {"deleted": days.water_view(row), "day": day_status(days.local(row["drunk_at"]).date())}
