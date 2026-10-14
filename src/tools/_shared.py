"""Shared parameter types and the tool decorator for the nutrition tools."""
import datetime as dt
import functools
from typing import Annotated, Callable

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from days import NutritionError
from server_instance import server


def doc(text: str):
    """Field with a description for the tool schema (keeps the signatures readable)."""
    return Field(description=text)


Date = Annotated[dt.date | None, doc("Day as 'YYYY-MM-DD' in the user's time zone; "
                                     "default today.")]
EndDate = Annotated[dt.date | None, doc("Last day of a range as 'YYYY-MM-DD' (inclusive); "
                                        "default = date (one day only).")]
Time = Annotated[str | None, doc("Time of day as 'HH:MM', e.g. '07:30'; default now (for "
                                 "another day than today: 12:00).")]
MealId = Annotated[int, doc("meal_id of the meal, as meal_list, meal_search or meal_log "
                            "return it.")]
WaterId = Annotated[int, doc("water_id of the entry, as water_list or water_log return it.")]


def nutrition_tool(func: Callable) -> Callable:
    """Register func as an MCP tool; NutritionError reaches the agent as ToolError."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NutritionError as exc:
            raise ToolError(str(exc)) from exc
    server.tool()(wrapper)
    return wrapper
