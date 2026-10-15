"""Central configuration for the mcp-nutrition project.

Environment variables are read once here so the rest of the codebase can rely
on validated, well-known settings instead of scattering os.getenv() calls
across modules.
"""
import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# === LOGGING ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# === DATABASE ===
# libpq connection string of the Postgres database that holds the schema "nutrition", e.g.
# postgresql://nutrition:<password>@127.0.0.1:5433/nutrition. Kept in the .env next to the
# release.
DATABASE_URL = os.getenv("NUTRITION_DATABASE_URL", "")

# === TIME ===
# The user's time zone: "today", dates and times of meals and water are meant in it.
TIMEZONE = ZoneInfo(os.getenv("NUTRITION_TIMEZONE", "Europe/Vienna"))
