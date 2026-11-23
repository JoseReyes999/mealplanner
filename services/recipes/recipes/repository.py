"""All SQL for the recipes domain. Every function receives the connection as `conn`,
so it can be tested without Flask. Placeholders are %s (pymssql), never string formatting."""

# created_at as 'YYYY-MM-DD HH:MM:SS' text (style 120), the same shape the API returned in Assignment 1.
CREATED_AT = "CONVERT(VARCHAR(19), created_at, 120) AS created_at"


def get_or_create_ingredient(conn, name):
    """Return the id of the ingredient called `name`, creating it if it doesn't exist.

    The comparison ignores case because ingredients.name has a case-insensitive collation.
    """
    name = name.strip()
    row = conn.execute("SELECT id FROM ingredients WHERE name = %s", (name,)).fetchone()
    if row:
        return row["id"]
    # OUTPUT INSERTED.id returns the new IDENTITY value (SQLite's lastrowid).
    return conn.execute(
        "INSERT INTO ingredients (name) OUTPUT INSERTED.id VALUES (%s)", (name,)
    ).fetchone()["id"]


def _insert_lines(conn, recipe_id, ingredients):
    for item in ingredients:
        ingredient_id = get_or_create_ingredient(conn, item["name"])
        conn.execute(
            "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) "
            "VALUES (%s, %s, %s, %s)",
            (recipe_id, ingredient_id, item["quantity"], item["unit"]),
        )


def create_recipe(conn, name, base_servings, instructions, ingredients):
    """Insert a recipe and its ingredient lines in one transaction. Returns the new id."""
    with conn:  # commits if everything succeeds, rolls back if anything fails
        recipe_id = conn.execute(
            "INSERT INTO recipes (name, base_servings, instructions) OUTPUT INSERTED.id "
            "VALUES (%s, %s, %s)",
            (name, base_servings, instructions),
        ).fetchone()["id"]
        _insert_lines(conn, recipe_id, ingredients)
    return recipe_id


def list_recipes(conn):
    """All recipes, alphabetically, without their ingredients."""
    return conn.execute(
        f"SELECT id, name, base_servings, {CREATED_AT} FROM recipes ORDER BY name"
    ).fetchall()


def get_recipe(conn, recipe_id):
    """One recipe with its ingredient lines, or None if it doesn't exist."""
    recipe = conn.execute(
        f"SELECT id, name, base_servings, instructions, {CREATED_AT} FROM recipes WHERE id = %s",
        (recipe_id,),
    ).fetchone()
    if recipe is None:
        return None
    recipe["ingredients"] = conn.execute(
        """
        SELECT i.id AS ingredient_id, i.name, ri.quantity, ri.unit
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = %s
        ORDER BY i.name
        """,
        (recipe_id,),
    ).fetchall()
    return recipe


def update_recipe(conn, recipe_id, name, base_servings, instructions, ingredients):
    """Replace a recipe's fields and all its ingredient lines. Returns False if it doesn't exist."""
    with conn:
        cursor = conn.execute(
            "UPDATE recipes SET name = %s, base_servings = %s, instructions = %s WHERE id = %s",
            (name, base_servings, instructions, recipe_id),
        )
        if cursor.rowcount == 0:
            return False
        # Simplest correct approach: delete the old lines and insert the new ones.
        conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = %s", (recipe_id,))
        _insert_lines(conn, recipe_id, ingredients)
    return True


def delete_recipe(conn, recipe_id):
    """Delete a recipe. Its lines go too (ON DELETE CASCADE). Returns False if it didn't exist."""
    with conn:
        cursor = conn.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    return cursor.rowcount > 0
