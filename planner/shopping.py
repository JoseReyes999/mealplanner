"""Build a week's shopping list. Pure functions: no Flask, no database.

Steps:
1. collect_lines: for every plan entry, ask the recipes domain for its ingredients
   already scaled to that entry's servings.
2. build_shopping_list: convert every line to its base unit, add up lines with the
   same ingredient AND the same unit family, then pick a readable unit.
"""
from planner.units import to_base, to_display


def collect_lines(entries, get_scaled_ingredients):
    """Gather the scaled ingredient lines of every entry.

    `get_scaled_ingredients` is passed in (normally recipes.service.get_scaled_ingredients),
    so this function can be tested with a fake one and no database.

    Returns (lines, missing): entries whose recipe was deleted go to `missing`
    instead of breaking the list (recipe_id is a soft reference).
    """
    lines, missing = [], []
    for entry in entries:
        scaled = get_scaled_ingredients(entry["recipe_id"], entry["servings"])
        if scaled is None:
            missing.append(entry)
        else:
            lines.extend(scaled)
    return lines, missing


def build_shopping_list(lines):
    """Merge ingredient lines into one shopping list.

    500 g flour + 1 kg flour      -> 1.5 kg flour   (same ingredient, same family)
    2 pcs egg   + 100 g egg       -> two lines      (count and mass can't be added)

    Returns [{'name': 'flour', 'quantity': 1.5, 'unit': 'kg'}, ...] sorted by name.
    """
    totals = {}  # (ingredient_id, family) -> {'name', 'family', 'base'}
    for line in lines:
        family, base_quantity = to_base(line["quantity"], line["unit"])
        key = (line["ingredient_id"], family)
        if key not in totals:
            totals[key] = {"name": line["name"], "family": family, "base": 0}
        totals[key]["base"] += base_quantity

    shopping_list = []
    for total in totals.values():
        quantity, unit = to_display(total["family"], total["base"])
        shopping_list.append({"name": total["name"], "quantity": quantity, "unit": unit})
    shopping_list.sort(key=lambda item: (item["name"].lower(), item["unit"]))
    return shopping_list