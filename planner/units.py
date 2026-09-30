"""Unit conversion for the shopping list. Pure functions: no Flask, no database.

Every unit belongs to a FAMILY and has a FACTOR to that family's base unit.
Only units in the same family can be added together.
"""
import math

# unit -> (family, how many base units one of this unit is)
# Must contain the same units as the CHECK constraint in schema.sql.
UNITS = {
    "g": ("mass", 1),
    "kg": ("mass", 1000),
    "ml": ("volume", 1),
    "l": ("volume", 1000),
    "tsp": ("volume", 5),
    "tbsp": ("volume", 15),
    "pcs": ("count", 1),
}


def to_base(quantity, unit):
    """Convert to the family's base unit: (0.5, 'kg') -> ('mass', 500.0)."""
    if unit not in UNITS:
        raise ValueError(f"unknown unit '{unit}'")
    family, factor = UNITS[unit]
    return family, quantity * factor


def to_display(family, base_quantity):
    """Pick a readable unit for a base quantity: ('mass', 1500) -> (1.5, 'kg').

    - mass:   under 1000 g stays in g, otherwise kg
    - volume: under 1000 ml stays in ml, otherwise l
    - count:  always rounded UP, because you can't buy 1.5 eggs
    """
    if family == "mass":
        if base_quantity >= 1000:
            return round(base_quantity / 1000, 2), "kg"
        return round(base_quantity, 2), "g"
    if family == "volume":
        if base_quantity >= 1000:
            return round(base_quantity / 1000, 2), "l"
        return round(base_quantity, 2), "ml"
    if family == "count":
        # round() first so float noise like 3.0000000001 doesn't become 4
        return math.ceil(round(base_quantity, 6)), "pcs"
    raise ValueError(f"unknown family '{family}'")