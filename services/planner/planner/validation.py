"""Turns raw planner form input into clean data. Pure functions: no Flask, no database."""
from datetime import date

# Must match the CHECK constraints on plan_entries in schema.sql.
# Order matters: it's the order days and meals are shown in.
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MEAL_SLOTS = ("breakfast", "lunch", "dinner")


def parse_plan_form(form):
    """Validate the 'new plan' form. Returns (data, errors).

    week_start must be a Monday, so every plan covers exactly one Monday-Sunday week.
    """
    errors = []

    name = form.get("name", "").strip()
    if not name:
        errors.append("Name is required.")

    week_start = form.get("week_start", "").strip()
    try:
        if date.fromisoformat(week_start).weekday() != 0:  # 0 = Monday
            errors.append("The week must start on a Monday.")
    except ValueError:
        errors.append("Week start must be a date like 2026-10-05.")

    return {"name": name, "week_start": week_start}, errors


def parse_entry_form(form):
    """Validate the 'add a recipe to a meal' form. Returns (data, errors).

    Only checks the shape of the input. Whether the recipe exists is asked to the
    recipes domain (service.recipe_exists) by the route, not here.
    """
    errors = []

    day = form.get("day", "")
    if day not in DAYS:
        errors.append("Choose a valid day.")

    meal_slot = form.get("meal_slot", "")
    if meal_slot not in MEAL_SLOTS:
        errors.append("Choose a valid meal.")

    recipe_id = None
    try:
        recipe_id = int(form.get("recipe_id", ""))
    except ValueError:
        errors.append("Choose a recipe.")

    servings = None
    try:
        servings = int(form.get("servings", ""))
        if servings <= 0:
            errors.append("Servings must be greater than 0.")
    except ValueError:
        errors.append("Servings must be a whole number.")

    data = {"day": day, "meal_slot": meal_slot, "recipe_id": recipe_id, "servings": servings}
    return data, errors