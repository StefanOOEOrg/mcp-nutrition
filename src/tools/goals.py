"""Goal tools: the user's daily targets for energy, macros, fibre, sugar and water."""
from typing import Annotated

import db
from days import NutritionError
from tools._shared import doc, nutrition_tool

GOALS_DOC = {
    "kcal": "Daily energy goal in kcal.",
    "protein_g": "Daily protein goal in g (a minimum).",
    "carbs_g": "Daily carbohydrate goal in g.",
    "fat_g": "Daily fat goal in g.",
    "fiber_g": "Daily fibre goal in g (a minimum).",
    "sugar_g": "Daily sugar limit in g.",
    "water_ml": "Daily water goal in ml.",
}


def _clean(goals: dict) -> dict:
    return {k: (int(v) if float(v).is_integer() else float(v)) if v is not None else None
            for k, v in goals.items()}


@nutrition_tool
def goals_get() -> dict:
    """The user's daily goals; a goal that is not set is null."""
    return _clean(db.get_goals())


@nutrition_tool
def goals_set(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    kcal: Annotated[float | None, doc(GOALS_DOC["kcal"])] = None,
    protein_g: Annotated[float | None, doc(GOALS_DOC["protein_g"])] = None,
    carbs_g: Annotated[float | None, doc(GOALS_DOC["carbs_g"])] = None,
    fat_g: Annotated[float | None, doc(GOALS_DOC["fat_g"])] = None,
    fiber_g: Annotated[float | None, doc(GOALS_DOC["fiber_g"])] = None,
    sugar_g: Annotated[float | None, doc(GOALS_DOC["sugar_g"])] = None,
    water_ml: Annotated[int | None, doc(GOALS_DOC["water_ml"])] = None,
    clear: Annotated[list[str] | None, doc("Names of goals to remove, e.g. ['carbs_g'].")]
    = None,
) -> dict:
    """Change daily goals - only when the user asks for it. Only the given goals change;
    `clear` removes goals. Returns all goals afterwards."""
    changes = {k: v for k, v in {"kcal": kcal, "protein_g": protein_g, "carbs_g": carbs_g,
                                 "fat_g": fat_g, "fiber_g": fiber_g, "sugar_g": sugar_g,
                                 "water_ml": water_ml}.items() if v is not None}
    for name in clear or []:
        if name not in GOALS_DOC:
            raise NutritionError(f"There is no goal '{name}'. Goals: {', '.join(GOALS_DOC)}.")
        changes[name] = None
    if not changes:
        raise NutritionError("Nothing to change: give at least one goal or `clear`.")
    return _clean(db.set_goals(changes))
