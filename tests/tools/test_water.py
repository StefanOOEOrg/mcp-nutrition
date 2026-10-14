"""Tests for the water tools."""
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tools.goals import goals_set
from tools.water import water_delete, water_list, water_log


def test_log_list_delete():
    """Entries add up per day against the water goal; deleted entries are gone."""
    goals_set(water_ml=3000)
    water_log(500, time="07:00")
    result = water_log(750)
    assert result["day"]["goals"]["water_ml"] == {"goal": 3000, "so_far": 1250, "left": 1750}
    assert water_list()["total_ml"] == 1250
    water_delete(result["logged"]["water_id"])
    assert [e["ml"] for e in water_list()["entries"]] == [500]


def test_refuses_implausible_amounts_and_unknown_ids():
    """0 ml, absurd amounts and unknown water_id are refused."""
    with pytest.raises(ToolError, match="not plausible"):
        water_log(0)
    with pytest.raises(ToolError, match="water_id 3"):
        water_delete(3)
