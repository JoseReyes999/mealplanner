"""All SQL for the recipes domain. Every function receives the connection as `conn`,
so it can be tested without Flask."""


def get_or_create_ingredient(conn, name):
    """Return the id of the ingredient called `name`, creating it if it doesn't exist.

    The comparison ignores case because ingredients.name is COLLATE NOCASE.
    """
    name = name.strip()
    row = conn.execute("SELECT id FROM ingredients WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO ingredients (name) VALUES (?)", (name,)).lastrowid


def _insert_lines(conn, recipe_id, ingredients):
    for item in ingredients:
        ingredient_id = get_or_create_ingredient(conn, item["name"])
        conn.execute(
            "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) "
            "VALUES (?, ?, ?, ?)",
            (recipe_id, ingredient_id, item["quantity"], item["unit"]),
        )


def create_recipe(conn, name, base_servings, instructions, ingredients):
    """Insert a recipe and its ingredient lines in one transaction. Returns the new id."""
    with conn:  # commits if everything succeeds, rolls back if anything fails
        recipe_id = conn.execute(
            "INSERT INTO recipes (name, base_servings, instructions) VALUES (?, ?, ?)",
            (name, base_servings, instructions),
        ).lastrowid
        _insert_lines(conn, recipe_id, ingredients)
    return recipe_id


def list_recipes(conn):
    """All recipes, alphabetically, without their ingredients."""
    rows = conn.execute(
        "SELECT id, name, base_servings, created_at FROM recipes ORDER BY name COLLATE NOCASE"
    ).fetchall()
    return [dict(row) for row in rows]


def get_recipe(conn, recipe_id):
    """One recipe with its ingredient lines, or None if it doesn't exist."""
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        return None
    recipe = dict(row)
    lines = conn.execute(
        """
        SELECT i.id AS ingredient_id, i.name, ri.quantity, ri.unit
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY i.name COLLATE NOCASE
        """,
        (recipe_id,),
    ).fetchall()
    recipe["ingredients"] = [dict(line) for line in lines]
    return recipe


def update_recipe(conn, recipe_id, name, base_servings, instructions, ingredients):
    """Replace a recipe's fields and all its ingredient lines. Returns False if it doesn't exist."""
    with conn:
        cursor = conn.execute(
            "UPDATE recipes SET name = ?, base_servings = ?, instructions = ? WHERE id = ?",
            (name, base_servings, instructions, recipe_id),
        )
        if cursor.rowcount == 0:
            return False
        # Simplest correct approach: delete the old lines and insert the new ones.
        conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
        _insert_lines(conn, recipe_id, ingredients)
    return True


def delete_recipe(conn, recipe_id):
    """Delete a recipe. Its lines go too (ON DELETE CASCADE). Returns False if it didn't exist."""
    with conn:
        cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    return cursor.rowcount > 0