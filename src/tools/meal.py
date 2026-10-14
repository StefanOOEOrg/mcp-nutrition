"""Meal tools: record, list, search, correct and delete meals."""
from typing import Annotated, Literal

import db
import days
from days import NutritionError
from tools._shared import Date, EndDate, MealId, Time, doc, nutrition_tool
from tools.day import day_status

MealType = Literal["breakfast", "lunch", "dinner", "snack", "drink"]

Kcal = Annotated[float, doc("Energy in kcal (total of the meal; from food_nutrition's total).")]
Protein = Annotated[float, doc("Protein in g (total of the meal).")]
Carbs = Annotated[float, doc("Carbohydrates in g (total of the meal).")]
Fat = Annotated[float, doc("Fat in g (total of the meal).")]
Fiber = Annotated[float | None, doc("Fibre in g, if known.")]
Sugar = Annotated[float | None, doc("Sugar in g, if known.")]
Alcohol = Annotated[float | None, doc("Alcohol in g, if any.")]
Caffeine = Annotated[float | None, doc("Caffeine in mg, if any (coffee ~ 80-100 mg/cup).")]
Name = Annotated[str, doc("Short name of the meal, e.g. 'Overnight Oats + Kaffee'.")]
Components = Annotated[str | None, doc("The single components with amounts, e.g. "
                                       "'Haferflocken 60 g, Skyr 150 g, Heidelbeeren 100 g'.")]
Estimated = Annotated[bool, doc("true if the values are estimated rather than taken from "
                                "mcp-food.")]
Notes = Annotated[str | None, doc("Free note, e.g. 'im Restaurant'.")]


@nutrition_tool
def meal_log(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: Name,
    kcal: Kcal,
    protein_g: Protein,
    carbs_g: Carbs,
    fat_g: Fat,
    meal_type: Annotated[MealType | None, doc(
        "Kind of meal. Default by time of day: before 10:30 breakfast, 11:00-14:30 lunch, "
        "17:30-21:30 dinner, otherwise snack. 'drink' for drinks with energy (shake, juice, "
        "sports drink); plain water goes to water_log.")] = None,
    date: Date = None,
    time: Time = None,
    components: Components = None,
    fiber_g: Fiber = None,
    sugar_g: Sugar = None,
    alcohol_g: Alcohol = None,
    caffeine_mg: Caffeine = None,
    estimated: Estimated = False,
    notes: Notes = None,
) -> dict:
    """Record one meal the user reported, with the total values of the meal. Returns the
    stored meal (with meal_id) and the totals of that day against the goals - enough to
    report the day's status without another call. To change a meal later use meal_update,
    not a second meal_log."""
    when = days.moment(date, time)
    row = db.insert_meal({
        "eaten_at": when, "meal_type": meal_type or days.meal_type_at(when),
        "name": name.strip(), "components": components, "kcal": kcal, "protein_g": protein_g,
        "carbs_g": carbs_g, "fat_g": fat_g, "fiber_g": fiber_g, "sugar_g": sugar_g,
        "alcohol_g": alcohol_g, "caffeine_mg": caffeine_mg, "estimated": estimated,
        "notes": notes,
    })
    return {"logged": days.meal_view(row), "day": day_status(when.date())}


@nutrition_tool
def meal_list(date: Date = None, end_date: EndDate = None) -> list[dict]:
    """The meals of one day (default today) or of a range of days, in time order, each with
    meal_id, date, time, meal_type, name, components and values. Totals: day_summary."""
    first, last = days.date_range(date, end_date)
    return [days.meal_view(row) for row in db.meals_between(first, last)]


@nutrition_tool
def meal_search(
    query: Annotated[str, doc("Words that must all appear in the name, components or notes, "
                              "e.g. 'oats' or 'pizza restaurant'.")],
    limit: Annotated[int, doc("Maximum number of meals.")] = 10,
) -> list[dict]:
    """Find earlier meals by words, newest first - e.g. to log 'the same as last Tuesday'
    again with the same values."""
    words = query.split()
    if not words:
        raise NutritionError("query is empty.")
    return [days.meal_view(row) for row in db.search_meals(words, limit)]


@nutrition_tool
def meal_update(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    meal_id: MealId,
    name: Annotated[str | None, doc("New name.")] = None,
    kcal: Annotated[float | None, doc("New energy in kcal.")] = None,
    protein_g: Annotated[float | None, doc("New protein in g.")] = None,
    carbs_g: Annotated[float | None, doc("New carbohydrates in g.")] = None,
    fat_g: Annotated[float | None, doc("New fat in g.")] = None,
    meal_type: Annotated[MealType | None, doc("New kind of meal.")] = None,
    date: Annotated[Date, doc("Move the meal to this day ('YYYY-MM-DD').")] = None,
    time: Annotated[Time, doc("Move the meal to this time ('HH:MM').")] = None,
    components: Components = None,
    fiber_g: Fiber = None,
    sugar_g: Sugar = None,
    alcohol_g: Alcohol = None,
    caffeine_mg: Caffeine = None,
    estimated: Annotated[bool | None, doc("Mark the values as estimated (true) or not "
                                          "(false).")] = None,
    notes: Notes = None,
) -> dict:
    """Correct a recorded meal: only the fields that are given change, everything else stays
    (to change the amount, give the new totals kcal, protein_g, carbs_g, fat_g). Returns the
    updated meal and the totals of its day."""
    meal = db.get_meal(meal_id)
    if not meal:
        raise NutritionError(f"There is no meal with meal_id {meal_id}: meal_list shows the "
                             "meals of a day with their meal_id.")
    changes = {k: v for k, v in {
        "name": name, "kcal": kcal, "protein_g": protein_g, "carbs_g": carbs_g, "fat_g": fat_g,
        "meal_type": meal_type, "components": components, "fiber_g": fiber_g,
        "sugar_g": sugar_g, "alcohol_g": alcohol_g, "caffeine_mg": caffeine_mg,
        "estimated": estimated, "notes": notes}.items() if v is not None}
    if date is not None or time is not None:
        before = days.local(meal["eaten_at"])
        changes["eaten_at"] = days.moment(date or before.date(), time or f"{before:%H:%M}")
    if not changes:
        raise NutritionError("Nothing to change: give at least one field besides meal_id.")
    row = db.update_meal(meal_id, changes)
    return {"updated": days.meal_view(row),
            "day": day_status(days.local(row["eaten_at"]).date())}


@nutrition_tool
def meal_delete(meal_id: MealId) -> dict:
    """Delete a recorded meal for good (there is no undo). Returns what was deleted and the
    totals of its day afterwards."""
    meal = db.get_meal(meal_id)
    if not meal:
        raise NutritionError(f"There is no meal with meal_id {meal_id}.")
    db.delete_meal(meal_id)
    return {"deleted": days.meal_view(meal),
            "day": day_status(days.local(meal["eaten_at"]).date())}
