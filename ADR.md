## 1. Backend framework: Flask with server-rendered templates

Date: 2026-09-27
Status: Superseded by [6]
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
Status: Superseded by [7]
Context: The shopping list must merge the same ingredient across different recipes, and the flatmates can enter name inconsistently (like "flour" or "Flour") additionally, can enter units the app cannot convert. The sql schema must be able to compare the same ingredient even though it has different capital letters and reject bad units before Python handles any data.
Decision: I split the recipes domain into three tables: recipes, ingredients (name UNIQUE COLLATE NOCASE) and recipe_ingredients, a junction table with a composite primary key (recipe_id, ingredient_id), quantity > 0 and a CHECK-limited unit list. Deleting a recipe cascades to its ingredient lines, while deleting an ingredient still used by a recipe is restricted.
Alternatives considered: Storing the ingredients in recipe_ingredients as free text to have fewer tables, but I rejected this because then the case of "flour" and "Flour" would become different ingredients, so the shopping list would not be able to merge them.
Consequences: The shopping list can group lines by ingredient_id instead of comparing their string names. Additionally the database rejects invalid units or quantities. The cost is that this same units list must also be defined in Python and adding a new unit means rebuilding the table, because sqlite3 cannot alter a CHECK constraint.

Update (2026-10-01): the planner domain added two tables, meal_plans and plan_entries, where plan_entries.recipe_id points to a recipe without a FOREIGN KEY on purpose (a soft reference, see ADR-2), so the two domains share one SQLite file today but could be split into separate databases later; the cost is that the planner must handle deleted recipes itself, which it does by showing "(deleted recipe)" and leaving them out of the shopping list.

## 4. Test businnes logic directly, against real temporary sqlite3 database

Date: 2026-09-28
Status: Superseded by [9]
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

## 6. The split: two services along the ADR-2 seam

Date: 2026-11-23
Status: Decided
Context: Assignment 2 needs two independently deployable services, each with its own database. In Assignment 1 (ADR-2) the planner could only reach recipes through 4 functions in recipes/service.py, and plan_entries.recipe_id was already a soft reference.
Decision: The seam stayed where ADR-2 put it: recipes owns recipes and ingredients, planner owns plans and entries. The service functions became HTTP endpoints, so what crosses the seam is 3 GET calls from the planner: GET /recipes (names for the plan), GET /recipes/{id} (does the recipe exist) and GET /recipes/{id}/scaled?servings=N (ingredients for the shopping list). recipes_client.py kept the same function names, so shopping.py did not change. The planner finds recipes through RECIPES_URL and every call has a 2 s timeout. The Flask templates were replaced by JSON APIs and a static UI, since the UI now runs on a storage static website and calls both services from the browser (ADR-1 superseded).
ADR-2 held: the split only swapped function calls for HTTP calls and moved each domain into its own folder. No business logic moved.
Alternatives considered: Moving the shopping list into recipes, rejected because recipes would then need plan data and the dependency would just flip. Caching recipe names in the planner, not built (ADR-10).
Consequences: Each service deploys and fails on its own, and recipes being down no longer breaks the plan page. The cost is that the shopping list makes one HTTP call per planned meal (up to 21 a week), and the two APIs must stay in sync, which the OpenAPI documents and their tests cover.

## 7. Data and migrations: one SQL Server database per service

Date: 2026-11-23
Status: Decided
Context: Before, one SQLite file held all 5 tables and the schema was created on every boot with CREATE TABLE IF NOT EXISTS. Now each service needs its own database and login, and once a database holds data the schema has to change without losing it.
Decision: Each service has its own SQL Server database (a container locally, Azure SQL serverless on Azure) and its own contained user (recipes*app, planner_app) with access only to its own database; logging in as recipes_app to the planner database fails. The Assignment 1 data was only test data, so instead of copying it each service starts from 001_init.sql, the same schema in SQL Server syntax (INT IDENTITY, NVARCHAR, MERGE instead of ON CONFLICT, OUTPUT INSERTED.id instead of lastrowid). migrate.py applies the files in migrations/ in order at startup, records each one in schema_migrations so it never runs twice, and runs each file in one transaction so a broken file leaves nothing half-applied. This is safe because there is at most 1 replica.
Integrity lost at the seam: plan_entries.recipe_id can't have a foreign key to a table in another database, and deleting a recipe can't cascade into plans. To compensate, the planner asks recipes whether a recipe exists before saving an entry (503 and nothing saved if recipes is down), shows deleted recipes as "(deleted recipe)", and leaves them out of the shopping list. Everything else (CHECKs, unique ingredient names, cascades) is still enforced inside each database.
Recovery plan for a bad migration: migrations are forward-only. A migration that fails rolls back, the container doesn't start and the CD health check fails, so I fix the file or revert and deploy again. A migration that ran but was wrong is fixed with a new file (003*...), never by editing one that already ran. Lost data can be recovered with Azure SQL point-in-time restore. Changes are additive (new columns with a DEFAULT, nothing dropped), like 002.
Alternatives considered: Keeping SQLite inside the container, rejected because the container is replaced on every deploy and scales to zero, so the data would be lost.
Consequences: Tests now need SQL Server (Docker locally, a service container in CI), startup is a bit slower, and no query can join across the two domains. In return, schema changes are versioned files that apply the same way locally, in CI and on Azure.

## 8. Serverless hosting on Azure

Date: 2026-11-25
Status: Decided
Context: The system runs on my Azure for Students subscription and should only cost money when it is used. The professor's deployment guide defines the shape (storage static website, Container Apps, Azure SQL serverless), replacing the Static Web Apps in the assignment text.
Decision: Everything is in rg-jmreyes-ieu2024 (francecentral). The UI is a static website on the storage account jmreyesieu2024ui (cents per GB). The two services run in Container Apps (jmreyes-ieu2024-recipes and -planner) with min 0 and max 1 replica, billed per second only while running, with no Log Analytics workspace. Each service has its own serverless database on jmreyes-ieu2024-sql using the free offer: it pauses after 60 minutes idle and pauses instead of billing when the free allowance runs out. Images are on GHCR and the pipeline signs in with a managed identity, so no password is stored.
Consequences: Scale-to-zero means cold starts. The first request starts the container and Azure answers 503 "App port is not ready" until it is ready, so the UI retries page loads for about 30 seconds (never saves). A paused database answers error 40613 for about a minute (I hit it myself), so db.connect retries with backoff and the CD health check waits up to about 10 minutes. Migrations run at startup, which is only safe because there is at most 1 replica. Logs only exist while a replica is running: the replica that logged migration 002 was gone after scaling to zero, so I proved it with the schema_migrations table instead.
At 100x traffic: min replicas of at least 1 and more than 1 max replica, which means moving migrations out of startup into a separate step that runs once per deploy. The databases would leave the free offer, with more vCores and no auto-pause. I would also add a batch endpoint or cache for the shopping list (about 20 calls per list, ADR-10) and Log Analytics so logs survive.
Alternatives considered: App Service or provisioned SQL, rejected because they cost money even when idle. AKS, rejected as far too much for two small services.

## 9. Pipeline and testing

Date: 2026-11-25
Status: Decided
Context: Every push to main deploys to Azure, so CI has to stop broken changes before they get there. With two services, a real SQL Server and HTTP between them, ADR-4 (SQLite tests) is superseded.
Decision: CI runs on every branch push and pull request, and again in CD on main. It validates system.yaml against the course schema and both openapi.yaml files, lints with ruff, runs the tests against a real SQL Server container (same engine as Azure, because of MERGE, OUTPUT and IDENTITY), fails below 70% coverage of the service code (currently about 99%), and builds both images. CD then pushes SHA-tagged images, deploys with OIDC and fails unless /health answers 200 with that commit's SHA.
The cross-seam test replaces the recipes service with a stub (StubRecipesService) that answers the same paths and JSON shapes and checks every call has a timeout. With the stub up it tests the real flow (names, existence check, merged shopping list); with it down it tests the failure handling (plan still shown, adding returns 503 and saves nothing, shopping list returns 503). A stub is faster and more controllable than running both services in CI; the OpenAPI tests keep it honest by checking both sides of the seam match their documents.
Not tested on purpose: the UI JavaScript (checked by hand), Azure itself (CI never touches Azure SQL), cold start times, load, and the CD workflow (verified by running it).
Alternatives considered: SQLite or a mocked database in tests, rejected because they would pass while SQL Server-specific code breaks.
Consequences: each test job waits about a minute for SQL Server, and local tests need Docker. The CI password in the workflow is not a secret: it only exists in the throwaway CI container. In return, anything merged has passed the checks that protect the deploy.

## 10. Not built: a batch endpoint or cache for the shopping list

Date: 2026-11-26
Status: Decided
Context: To build a shopping list the planner calls GET /recipes/{id}/scaled once per planned meal. The Azure logs show it: one shopping list made about 20 calls to recipes in 1.5 seconds. If recipes is down or still waking up, the shopping list is not available at all.
Decision: I did not build either fix. One option is a batch endpoint (one POST /recipes/scaled with every recipe id and its servings, answered in one call). The other is a cache in the planner that keeps the last known ingredients of each recipe, so the shopping list could still be built when recipes is down.
Alternatives considered: The batch endpoint changes the contract on both sides of the seam (new endpoint, new OpenAPI entries, new tests) to save about a second for 4-6 users. The cache keeps a second copy of recipe data in the planner, which goes stale when a recipe is edited and needs rules for when to refresh it, which is the kind of coupling ADR-2 and ADR-6 avoid. For a shared flat, 1.5 seconds is acceptable and a clear 503 is an honest answer.
Consequences: The main consequence is that the shopping list function will be slow and it depends on recipes being up. It would be worth building the batch endpoint if the list takes more than 2-3 seconds or traffic grows (at 100x, 20 calls per list multiply quickly and keep recipes awake), and the cache if users need the shopping list even while recipes is down.
