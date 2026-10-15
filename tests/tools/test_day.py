"""Tests for day_summary, trend_get and the goals."""
import datetime as dt

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tools.day import day_summary, trend_get
from tools.goals import goals_get, goals_set
from tools.meal import meal_log
from tools.water import water_log


def test_summary_of_range_includes_empty_days_and_estimates():
    """Every day of the range appears; estimated meals are flagged."""
    meal_log("A", 2000, 100, 200, 80, date=dt.date(2026, 10, 11), fiber_g=25)
    meal_log("B", 500, 20, 50, 20, date=dt.date(2026, 10, 13), estimated=True)
    water_log(1000, date=dt.date(2026, 10, 12))
    result = day_summary(dt.date(2026, 10, 11), dt.date(2026, 10, 13))
    assert [(d["date"], d["weekday"], d["meals"]) for d in result] == [
        ("2026-10-11", "Sunday", 1), ("2026-10-12", "Monday", 0), ("2026-10-13", "Tuesday", 1)]
    assert result[0]["total"] == {"kcal": 2000, "protein_g": 100, "carbs_g": 200, "fat_g": 80,
                                  "fiber_g": 25, "water_ml": 0}
    assert result[1]["total"]["water_ml"] == 1000
    assert result[2]["contains_estimates"] is True and "goals" not in result[2]


def test_day_boundaries_follow_the_time_zone():
    """23:30 local time still belongs to that day (not to the UTC day)."""
    meal_log("Late", 300, 10, 30, 10, date=dt.date(2026, 10, 12), time="23:30")
    meal_log("Early", 200, 10, 20, 5, date=dt.date(2026, 10, 13), time="00:30")
    totals = [d["total"]["kcal"] for d in day_summary(dt.date(2026, 10, 12),
                                                      dt.date(2026, 10, 13))]
    assert totals == [300, 200]


def test_trend_averages_over_logged_days_until_yesterday():
    """Today is left out; the average counts only days with meals."""
    goals_set(kcal=2400)
    meal_log("A", 2000, 100, 200, 80, date=dt.date(2026, 10, 12))
    meal_log("B", 2400, 120, 250, 90, date=dt.date(2026, 10, 10))
    meal_log("Heute", 5000, 1, 1, 1)
    water_log(2100, date=dt.date(2026, 10, 12))
    trend = trend_get(7)
    assert (trend["from"], trend["to"], trend["days_with_meals"]) == ("2026-10-06",
                                                                      "2026-10-12", 2)
    assert trend["average_per_day"] == {"kcal": 2200, "protein_g": 110, "carbs_g": 225,
                                        "fat_g": 85}
    assert trend["average_water_ml"] == 300
    assert trend["lowest_kcal_day"] == {"date": "2026-10-12", "kcal": 2000}
    assert trend["goals"] == {"kcal": 2400}


def test_trend_without_meals():
    """No logged days: only the window and a zero count."""
    assert trend_get(14)["days_with_meals"] == 0


def test_goals_set_changes_only_given_and_clears():
    """goals_set keeps other goals; clear removes; unknown names are refused."""
    assert goals_get()["kcal"] is None
    goals_set(kcal=2400, protein_g=130, carbs_g=250)
    goals_set(fat_g=70, clear=["carbs_g"])
    assert goals_get() == {"kcal": 2400, "protein_g": 130, "carbs_g": None, "fat_g": 70,
                           "fiber_g": None, "sugar_g": None, "water_ml": None}
    with pytest.raises(ToolError, match="no goal 'zucker'"):
        goals_set(clear=["zucker"])
    with pytest.raises(ToolError, match="Nothing to change"):
        goals_set()
