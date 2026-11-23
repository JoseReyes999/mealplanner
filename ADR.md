## 1. Backend framework: Flask with server-rendered templates

Date: 2026-09-27
Status: Decided
Context: MealPlanner must hold a few HTML pages and read/write SQLite in a single process for a shared flat of 4-6 users with no heavy traffic. In order to do so, I am building a simple Python stack so I can build and explain myself.
Decision: I decided to use Flask with Jinja HTML templates and Python's built in sqlite3. With the connections handled through db.py using functions like connect, get_db, close_db, and init_db to help me manage the database.
Alternatives considered: Django rejected because its ORM, admin panel and user accounts are used for larger multi user platforms, while MealPlanner has a handful of tables and no logins. Therefore sqlite3 keeps the code more simple and the SQL more visible. Then FastAPI was rejected because it is designed for async JSON APIs, when I render HTML files that don't need async. React rejected because it adds an extra JavaScript build step
Consequences: Flask gives me no ORM or admin, so I write my own SQL and form validation. Because the pages are plain templates, I can later implement JavaScript or JSON endpoints for a React frontend, without messing up the current structure.

## 2. Separate recipes and planner domains behind a service interface

Date: 2026-09-29
Status: Decided
Context: The assignment needs to have two separate domains that could later be split into individual microservices. In the case of MealPlanner, the planner needs recipe data (ingredients, servings) to build shopping list.
Decision: Each domain will be its own package(routes, repository, etc.) and the planner only accesses recipes through recipes/service.py which returns only a plain dict. Which is enforced by the test_planner_only_uses_recipes_service in tests/test_recipes_service.py.
Alternatives considered: The planner could access the recipe tables directly with a JOIN, which would be simpler (only one query) but this would mean that the planner would be directly tied to the recipes tables, meaning that any schema changes would require modification in the planner as well.
Consequences: Enables: splitting in the future now only means replacing four functions (list_recipe_choices, recipe_exists, get_recipe_ingredients, get_scaled_ingredients) with HTTP calls. The planner stores recipe_id as a soft reference with no foreign key, so a deleted recipe shows as '(deleted recipe)' and is skipped in the shopping list.Costs: extra layer of code and no single SQL query across both domains.

## 3. Store ingredients in their own table and enforce integrity in SQLite

Date: 2026-09-28
Status: Decided
Context: The shopping list must merge the same ingredient across different recipes, and the flatmates can enter name inconsistently (like "flour" or "Flour") additionally, can enter units the app cannot convert. The sql schema must be able to compare the same ingredient even though it has different capital letters and reject bad units before Python handles any data.
Decision: I split the recipes domain into three tables: recipes, ingredients (name UNIQUE COLLATE NOCASE) and recipe_ingredients, a junction table with a composite primary key (recipe_id, ingredient_id), quantity > 0 and a CHECK-limited unit list. Deleting a recipe cascades to its ingredient lines, while deleting an ingredient still used by a recipe is restricted.
Alternatives considered: Storing the ingredients in recipe_ingredients as free text to have fewer tables, but I rejected this because then the case of "flour" and "Flour" would become different ingredients, so the shopping list would not be able to merge them.
Consequences: The shopping list can group lines by ingredient_id instead of comparing their string names. Additionally the database rejects invalid units or quantities. The cost is that this same units list must also be defined in Python and adding a new unit means rebuilding the table, because sqlite3 cannot alter a CHECK constraint.

Update (2026-10-01): the planner domain added two tables, meal_plans and plan_entries, where plan_entries.recipe_id points to a recipe without a FOREIGN KEY on purpose (a soft reference, see ADR-2), so the two domains share one SQLite file today but could be split into separate databases later; the cost is that the planner must handle deleted recipes itself, which it does by showing "(deleted recipe)" and leaving them out of the shopping list.

## 4. Test businnes logic directly, against real temporary sqlite3 database

Date: 2026-09-28
Status: Decided
Context: The assignment requires a 70% test coverage on business logic, for the case of MealPlanner, the logic is based mostly in calculations (parsing ingredient lines, scaling, unit conversion, and merging the shopping list) where an error produces a bad list with no visible error. Several important rules (CASCADE, RESTRICT, CHECK, COLLATE, NOCASE) are enforced by SQLite itself, so they can be verifieda against a real database.
Decision: The tests go in three levels. First, pure functions with no database (validation.py, scaling.py, untis.py, and shopping.py), since they have the main logic and run fastest. Second, the repositories against a real temporary SQLite file created with pytest's tmp_path, so that this way the restrictions mentioned beefore could actually be exercised. Lastly, a few end to end page tests with Flask's test client, and a test in planner that verifies planner only imports service.py from recipes.py.
Alternatives considered: Mocking the database, rejected because the integrity rules live inside the SQLite, so a mock would pass regardless if the schema is wrong. Testing only through the web pages, rejected because those tests are slower and if one fails it is hard to determine what caused it (logic, SQL, or template).
Consequences: Suit has 107 tests with about 99% coverage. Which in one case helped me catch a real bug: detail.html contained the list template. What I left thinner is the visual layout of the HTML and the if **name** == "**main**" start line, which are framework glue rather than business logic

## 5. Do not build user log in

Date: 2026-10-02
Status: Decided
Context: MealPlanner is used by a shared flat of 4-6 flatmates who trust each other, and it holds no sensitive or personal user data, only recipies and meal plans. Adding accounts would mean adding owners to recipes and plans.
Decision: I did not build login or user accounts. Everyone who opens the app can see, create and edit a recipe or meal plan.
Alternatives considered: Buidling login with a users table, password hashing and Flask sessions. Rejected because it adds a third domain of code. It would involve security risks and more testing to be done for a flat where everything is already shared.
Consequences: The code stays simpler and there is no password to protect, making assignment 2 deplopyment simpler. The cost is that anyone with the link can edit or delete a recipe, so if the app would go public, login should be implemented before.

## 6. The split: two services along the ADR-2

Date: 2026-11-23
Status: Decided
Context: Assignment 2 specifies that we need two independent deployable services were each contain their own database. In assignment 1, we made it clear that communication between planner and recipes was strictly through 4 functions in recipe/service.py and plan_entries.recipe_id.
Decision: The separation from ADR-2 persists, `recipes` owns reciped and ingredients, while `planner` owns plans and entries. The service functions used before became HTTP endpoints. So now in order to cross this separation is 3 GET calls: `GET /recipes` (recipes in plan grid), `GET /recipes/{id}` (recipe exists), and `GET /recipes/{id}/scaled?servings=N` (scaled version of the ingredients for each planned meal). `recipes_client.py` kept the same function names so that `shopping.py` did not need any change, `get_recipe_ingredients` function was deleted because shopping list only needs the scaled version. The planner finds recipes through environment variable `RECIPES_URL` (http://recipes:8000 in compose, the Container App URL on Azure). Every call has a 2 s timeout. The Flask templates were replaced by JSON APIs and a static UI (ui/), this decision was made because the UI runs on a storage static website that calls both services from the services, making ADR-1 superseded.
Alternatives considered: One of the alternatives considered was to move the shopping list into recipes: rejected because recipes would then need plan data, which would just flip the dependency. One other alternatice is to keep a copy or cache of the recipe names: this has not been built being a good candidate for ADR-10.
Consequences: Thanks to these decisions, each service can be deployed, scaled and fails on their own, and recipes going down no longer breaks the plan page. One of its cost is that the shopping list makes one HTTP call per planned meal, up to 21 for a full week, so it’s slower than one SQL query and depends on recipes being up.Another cost is two contracts to keep in sync. The openapi.yaml files plus the tests that compare them with the routes cover that. the cross-seam integration test replaces recipes with a stub that answers the same HTTP endpoints (details in ADR-9).

## 7. Data and migrations: one SQL Server database per service, versioned migrations

Date: 2026-11-23
Status: Decided
Context: Before I only had one SQL file all 5 tables, and the schema createde on every boot the tables with the condition CREATE TABLE IF NOT EXISTS. Now each service needs its own database and login. Once the database holds the data, the schema has to change without losing it. IF NOT EXISTS cannot alter an existing table.
Decision: One database per service, SQL Server runs as a container locally and as Azure SQL serverless on Azure. Each service logs in with its own contained user (recipes_app, planner_app), which has access only to their own database. I tested this by trying to access planner db through recipes container. Each service starts with 001_init.sql because the data from Assignment 1 was only test data, this was done in SQL Server syntax:
INTEGER PRIMARY KEY → INT IDENTITY
TEXT → NVARCHAR, and week_start became a real DATE
COLLATE NOCASE → a case-insensitive collation
RESTRICT → NO ACTION
ON CONFLICT upsert → MERGE
lastrowid → OUTPUT INSERTED.id
The versioned migrations (migrate.py):
files named NNN_description.sql, applied in order at startup
each file recorded in schema_migrations, so a second start applies nothing
each file runs in one transaction, so a broken file leaves nothing half-applied (there’s a test for that)
safe at startup because there’s max 1 replica
Now there is no foreign key `plan_entries.recipe_id` to recipes because they exist in different databases and a deletion cannot cascade into plans. This is compensated by the following:
1.before saving an entry, the planner asks recipes whether the recipe exists (and if recipes is down: 503, nothing saved)
2.a deleted recipe shows as “(deleted recipe)” in the plan
3.deleted recipes are left out of the shopping list and counted in missing_recipes
Integrity is mantained through each entry (CHECK, unique ingredient name, cascade from recipe to its lines and plan to its entries).
Alternatives considered: One of the alternatives considered was to keep SQLite inside the container. This was rejected because the container is replaced on every deploy and scales to zero, so the file would be lost.
Consequences: Its costs is that now need SQL Server (Docker locally, and a service container in CI). The startup is slower beacuase of conections and migration checks. No SQL query can join across the two domains. In the other hand the gain is that schema changes are reviewed, versioned files that apply the same way locally, in CI and on Azure.
