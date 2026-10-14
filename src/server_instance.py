"""Shared MCPServer instance that tool modules register themselves against."""
from mcp.server.mcpserver import MCPServer

INSTRUCTIONS = """\
Food diary of the user: meals (with their nutrition values), water, daily goals and the
evaluation of days and weeks. This server records and evaluates; it does not know foods. The
values of a meal come from the server mcp-food (food_search → food_nutrition): its `total`
uses the same field names as meal_log (kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g).

Only record what the user reported. One meal_log per meal; put the single components into
`components`. If values had to be estimated, set estimated=true.

Dates are 'YYYY-MM-DD', times 'HH:MM', both in the user's time zone. Without a date a tool
means today; without a time meal_log/water_log take the current time. Every meal has a
meal_id and every water entry a water_id: meal_list / water_list show them, meal_update /
meal_delete / water_delete need them. To correct a meal, change it with meal_update instead
of logging it again.

Evaluation: day_summary for one or more days (totals against the goals, what is left),
trend_get for averages over the last 7/14/30 days. meal_log and water_log already return
the totals of the day, so no extra call is needed to report the day's status.
Body weight is not recorded here (it comes from Garmin).
"""

server = MCPServer(name="mcp-nutrition", instructions=INSTRUCTIONS)
