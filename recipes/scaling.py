"""Scale a recipe's ingredient quantities to a different number of servings. Pure functions."""


def scale_quantity(quantity, base_servings, target_servings):
    """Rule of three: quantity * target / base.

    200 g for 4 servings -> 300 g for 6 servings.
    """
    if base_servings <= 0 or target_servings <= 0:
        raise ValueError("servings must be greater than 0")
    return quantity * target_servings / base_servings


def scale_ingredients(ingredients, base_servings, target_servings):
    """Return a NEW list of ingredient dicts with every quantity scaled.

    The original list is not modified, so the caller's data stays intact.
    """
    return [
        {**item, "quantity": scale_quantity(item["quantity"], base_servings, target_servings)}
        for item in ingredients
    ]