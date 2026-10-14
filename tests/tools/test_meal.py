"""Tests for the meal tools."""
import datetime as dt

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tools.goals import goals_set
from tools.meal import meal_delete, meal_list, meal_log, meal_search, meal_update

YESTERDAY = dt.date(2026, 10, 12)


def test_log_defaults_to_now_and_type_by_time():
    """No date/time: today, now (08:15) → breakfast; the day totals come back right away."""
    goals_set(kcal=2400, protein_g=130)
    result = meal_log("Overnight Oats", 581, 47.5, 58, 16, components="Hafer 60 g, Skyr 150 g")
    assert result["logged"] == {"meal_id": 1, "date": "2026-10-13", "time": "08:15",
                                "meal_type": "breakfast", "name": "Overnight Oats",
                                "components": "Hafer 60 g, Skyr 150 g", "kcal": 581,
                                "protein_g": 47.5, "carbs_g": 58, "fat_g": 16}
    assert result["day"]["total"]["kcal"] == 581
    assert result["day"]["goals"]["kcal"] == {"goal": 2400, "so_far": 581, "left": 1819}


@pytest.mark.parametrize("time, meal_type", [("12:30", "lunch"), ("19:00", "dinner"),
                                             ("15:30", "snack"), ("23:30", "snack")])
def test_type_by_time(time, meal_type):
    """The default meal type follows the time of day."""
    assert meal_log("x", 1, 0, 0, 0, time=time)["logged"]["meal_type"] == meal_type


def test_other_day_without_time_is_noon():
    """A meal on another day without time is placed at 12:00 (lunch)."""
    logged = meal_log("Pizza", 900, 35, 100, 38, date=YESTERDAY)["logged"]
    assert (logged["date"], logged["time"], logged["meal_type"]) == ("2026-10-12", "12:00",
                                                                     "lunch")


def test_bad_time_is_refused():
    """Times must be HH:MM."""
    with pytest.raises(ToolError, match="HH:MM"):
        meal_log("x", 1, 0, 0, 0, time="halb acht")


def test_list_by_day_and_range():
    """meal_list shows one day by default, or a range."""
    meal_log("Gestern", 500, 20, 50, 20, date=YESTERDAY, time="19:00")
    meal_log("Heute", 300, 20, 30, 10, time="07:00")
    assert [m["name"] for m in meal_list()] == ["Heute"]
    assert [m["name"] for m in meal_list(YESTERDAY, dt.date(2026, 10, 13))] == ["Gestern",
                                                                                "Heute"]
    with pytest.raises(ToolError, match="before"):
        meal_list(dt.date(2026, 10, 13), YESTERDAY)


def test_search_matches_all_words_newest_first():
    """Every word must appear in name, components or notes."""
    meal_log("Pizza Margherita", 800, 30, 100, 30, date=YESTERDAY, notes="Restaurant")
    meal_log("Pizza Tonno", 850, 40, 100, 32)
    assert [m["name"] for m in meal_search("pizza")] == ["Pizza Tonno", "Pizza Margherita"]
    assert [m["name"] for m in meal_search("pizza restaurant")] == ["Pizza Margherita"]
    with pytest.raises(ToolError, match="empty"):
        meal_search("  ")


def test_update_changes_only_given_fields_and_moves_time():
    """meal_update keeps everything not given; date/time move the meal."""
    meal_id = meal_log("Shake", 450, 60, 30, 6, meal_type="drink", estimated=True)["logged"][
        "meal_id"]
    updated = meal_update(meal_id, kcal=500, time="10:00", estimated=False)["updated"]
    assert (updated["kcal"], updated["protein_g"], updated["time"], updated["meal_type"]) == (
        500, 60, "10:00", "drink")
    assert "estimated" not in updated
    moved = meal_update(meal_id, date=YESTERDAY)
    assert (moved["updated"]["date"], moved["updated"]["time"]) == ("2026-10-12", "10:00")
    assert moved["day"]["date"] == "2026-10-12"


def test_update_and_delete_refuse_unknown_ids_and_empty_changes():
    """Unknown meal_id and an update without fields are refused."""
    with pytest.raises(ToolError, match="meal_id 7"):
        meal_update(7, kcal=1)
    meal_id = meal_log("x", 1, 0, 0, 0)["logged"]["meal_id"]
    with pytest.raises(ToolError, match="Nothing to change"):
        meal_update(meal_id)
    with pytest.raises(ToolError, match="meal_id 8"):
        meal_delete(8)


def test_delete_returns_meal_and_new_day_total():
    """After meal_delete the day total no longer contains the meal."""
    meal_log("A", 300, 10, 10, 10)
    meal_id = meal_log("B", 200, 10, 10, 10)["logged"]["meal_id"]
    result = meal_delete(meal_id)
    assert result["deleted"]["name"] == "B" and result["day"]["total"]["kcal"] == 300


def test_components_from_food_nutrition_items_become_text():
    """A list (or one item) of food_nutrition items is stored as one line of text."""
    items = [{"recipe": "Overnight Oats Bowl", "amount": "0.5 portion(s)", "kcal": 290},
             {"name": "Kaffee mit Milch", "amount": "1 × 1 Tasse"},
             {"food_id": 7, "grams": 30}, "Zimt"]
    logged = meal_log("Oats", 300, 25, 30, 8, components=items)["logged"]
    assert logged["components"] == ("Overnight Oats Bowl 0.5 portion(s), Kaffee mit Milch "
                                    "1 × 1 Tasse, food_id 7 30 g, Zimt")
    single = meal_update(logged["meal_id"], components={"recipe": "Gregors Shake",
                                                       "servings": 1})["updated"]
    assert single["components"] == "Gregors Shake 1 ×"


def test_schema_allows_list_but_describes_text():
    """The schema accepts a list as a fallback; the description asks for one string."""
    import asyncio  # pylint: disable=import-outside-toplevel
    from mcp import Client  # pylint: disable=import-outside-toplevel
    import mcp_server  # pylint: disable=import-outside-toplevel

    async def schema():
        async with Client(mcp_server.server) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        return tools["meal_log"]

    tool = asyncio.run(schema())
    prop = tool.input_schema["properties"]["components"]
    assert {"type": "array"} in prop["anyOf"] and "not a list" in prop["description"]
    assert "Required: name, kcal, protein_g, carbs_g and fat_g" in " ".join(
        tool.description.split())
