## [N]. <Title>

Date: YYYY-MM-DD
Status: Decided
Context: 1-3 sentences, what forced this decision
Decision: 1-2 sentences, what you chose
Alternatives considered: at least one real alternative, and why you rejected it
Consequences: 1-2 sentences, what this costs or enables later

## 1. Project schema

Date: 2026-09-27
Status: Decided
Context: MealPlanner must hold a few HTML pages and read/write SQLite in a singl process for a shared flat of 4-6 users with no heavy traffic. In order to do so, I am building a simple Python stack so I can build and explain myself.
Decision: I decided to use Flask with Jinja HTML templates and Python's built in sqlite built in module. Where the connection is handled in db.py; where, there are functions like connect, get_db, close_db, and init_db¿ to help me manage the database.
Alternatives considered: Django was not an option because it offers many features that would be ideal for heavy traffic in users, but because MealPlanner needs a lot of tables and no logins, plain sqlite3 makes it simpler in terms of code and more managable from a database perspective. FastAPI rejected because it is designed for async JSON APIs, when I render HTML pages, so async is not necessary. React was also rejected because it adds additional Java Script build.
Consequence: Flask gives me no ORM or admin, so I write my own SQL and form validation. Because the pages are plain templates, I can later implement Java Script or JSON endpoints for a React frontend, without messing up the current structure.

## 2. Store ingredients in their own table and enforce integrity in SQLite

Date: 2026-09-28
Status: Decided
Context: The shopping list must merge the same ingredient across different recipes, and the flatmates can enter name inconsistently (like "flour" or "Flour") additionally, can enter units the app cannot convert. The sql schema must be able to compare the same ingredient even though it has different capital letters and reject bad units before Python handles any data.
Decision: I splitted the recipe domain into three tables: recipes, ingredients, and recipe_ingredients.

- recipes: id, name, base_servings (checks for value > 0), instructions, created_at (default TIMESTAMP)
- ingredients: id, name (UNIQUE COLLATE NOCASE)
- recipe_ingredients: recipe_id (foreign to recipes, ON DELETE CASCADE), ingredient_id (foreign to ingredients, ON DELETE RESTRICT), quantity (checks quantity > 0), unit CHECK (unit IN ('g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'pcs')), PRIMARY KEY(recipe_id, ingredient_id)
  Alternatives considered: Storing the ingredients in recipe_ingredients as free text to have fewer tables, but I rejected this because then the case of "flour" and "Flour" would become different ingredients.
  Consequence: The shopping list can group lines by ingredient_id insterad of comparing their string names. Additionally the database rejects invalid units or quantities. The cost is that this same units list must also be defined in Python and adding another metric means modifying these tables again.
