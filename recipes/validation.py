"""Turns raw form input into clean recipe data. Pure functions: no Flask, no database."""
import math

# Must match the CHECK constraint on recipe_ingredients.unit in schema.sql.
UNITS = ("g", "kg", "ml", "l", "tsp", "tbsp", "pcs")


def parse_ingredient_line(line):
    """Parse one line like '200 g flour' into {'quantity': 200.0, 'unit': 'g', 'name': 'flour'}.

    Raises ValueError with a readable message if the line is invalid.
    """
    parts = line.split(maxsplit=2)  # at most 3 pieces, so names can contain spaces
    if len(parts) < 3:
        raise ValueError(f"'{line}': use the format 'quantity unit name', e.g. '200 g flour'")
    raw_quantity, unit, name = parts

    try:
        quantity = float(raw_quantity.replace(",", "."))  # accept '0,5' as well as '0.5'
    except ValueError:
        raise ValueError(f"'{line}': '{raw_quantity}' is not a number")
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError(f"'{line}': quantity must be greater than 0")

    unit = unit.lower()
    if unit not in UNITS:
        raise ValueError(f"'{line}': unknown unit '{unit}' (use one of: {', '.join(UNITS)})")

    return {"quantity": quantity, "unit": unit, "name": name.strip()}


def format_ingredient_line(item):
    """The reverse of parse_ingredient_line, used to pre-fill the edit form: 200.0 -> '200 g flour'."""
    return f"{item['quantity']:g} {item['unit']} {item['name']}"


def parse_recipe_form(form):
    """Validate the whole recipe form.

    Returns (data, errors). If errors is empty, data can be passed straight to
    repository.create_recipe / update_recipe.
    """
    errors = []

    name = form.get("name", "").strip()
    if not name:
        errors.append("Name is required.")

    base_servings = None
    try:
        base_servings = int(form.get("base_servings", ""))
        if base_servings <= 0:
            errors.append("Servings must be greater than 0.")
    except ValueError:
        errors.append("Servings must be a whole number.")

    instructions = form.get("instructions", "").strip()
    if not instructions:
        errors.append("Instructions are required.")

    ingredients = []
    seen_names = set()
    lines = [line.strip() for line in form.get("ingredients", "").splitlines() if line.strip()]
    if not lines:
        errors.append("Add at least one ingredient.")
    for line in lines:
        try:
            item = parse_ingredient_line(line)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        key = item["name"].lower()  # same rule as COLLATE NOCASE in the database
        if key in seen_names:
            errors.append(f"'{item['name']}' is listed twice.")
            continue
        seen_names.add(key)
        ingredients.append(item)

    data = {
        "name": name,
        "base_servings": base_servings,
        "instructions": instructions,
        "ingredients": ingredients,
    }
    return data, errors