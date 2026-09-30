## 1. Backend framework: Flask with server-rendered templates

Date: 2026-09-27
Status: Decided
Context: MealPlanner must hold a few HTML pages and read/write SQLite in a singl process for a shared flat of 4-6 users with no heavy traffic. In order to do so, I am building a simple Python stack so I can build and explain myself.
Decision: I decided to use Flask with Jinja HTML templates and Python's built in sqlite3 built in module. With the connections handled through db.py using functions like connect, get_db, close_db, and init_db to help me manage the database.
Alternatives considered: Django rejected because it uses ORM, admin panel and user accounts are used for larger multi user platforms, MealPlanner has a lot of tables and no logins. Therefore sqlite3 keeps the code more simple and the SQL more visible. Then FastAPI was rejected because it is designed for async JSON APIs, when I render HTML files that don't need async. React rejected because it adds an extra JavaScript build step
Consequence: Flask gives me no ORM or admin, so I write my own SQL and form validation. Because the pages are plain templates, I can later implement Java Script or JSON endpoints for a React frontend, without messing up the current structure.

## 2. Separate recipes and planner domains behind a service interface

Date: 2026/09/29
Status: Decided
Context:The assignment needs to have two seperate domains that could later be split into individual microservices. In the case of MealPlanner, the planner needs recipe data (ingredients, servings) to build shopping list.
Decision: Each domain will be its own package(routes, repository, etc.) and the planner only accesses recipes through recipes/service.py which returns only a plain dict. Which is enforced by the test_recipes_service.py.
Alternatives considered: The planner could access the recipe tables directly with a JOIN, which would be simpler (only one query) but this would mean that the planner would be directly tied to the recipes tables, meaning that any schema changes would require modification in the planner aswell.
Consequences: Enables: splitting in the future now only means replcing three functions (list_recipe_choices, recipe_exists, get_recipe_ingredients) with HTTP calls. Costs: extra layer of code and no single SQL query across both domains.

## 3. Store ingredients in their own table and enforce integrity in SQLite

Date: 2026-09-28
Status: Decided
Context: The shopping list must merge the same ingredient across different recipes, and the flatmates can enter name inconsistently (like "flour" or "Flour") additionally, can enter units the app cannot convert. The sql schema must be able to compare the same ingredient even though it has different capital letters and reject bad units before Python handles any data.
Decision: I splitted the recipes domain into three tables: recipes, ingredients (name UNIQUE COLLATE NOCASE) and recipe_ingredients, a junction table with a composite primary key (recipe_id, ingredient_id), quantity > 0 and a CHECK-limited unit list. Deleting a recipe cascades to its ingredient lines, while deleting an ingredient still used by a recipe is restricted.
Alternatives considered: Storing the ingredients in recipe_ingredients as free text to have fewer tables, but I rejected this because then the case of "flour" and "Flour" would become different ingredients, so the shopping list would not be able to merge them.
Consequence: The shopping list can group lines by ingredient_id instead of comparing their string names. Additionally the database rejects invalid units or quantities. The cost is that this same units list must also be defined in Python and adding another metric means modifying these tables again.
