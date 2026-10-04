# MealPlanner

A small web app for a shared flat of 4–6 people to store recipes, plan the week's meals and get one merged shopping list.

It is a single Flask process with a SQLite database, built as the base for later DevOps work (containerisation and deployment in Assignment 2).

## Features

The app has two feature domains, kept separate so they could become independent services later (see `ADR.md`, entry 2).

**Recipes** (`recipes/`)

- Create, view, edit and delete recipes with a name, base servings, instructions and ingredients.
- Ingredients are typed one per line as `quantity unit name`, e.g. `200 g flour` or `0,5 kg potato`.
- Allowed units: `g`, `kg`, `ml`, `l`, `tsp`, `tbsp`, `pcs`.
- Ingredient names are matched case-insensitively, so "Flour" and "flour" are the same ingredient.

**Meal planner** (`planner/`)

- Create a weekly plan (the week must start on a Monday).
- Put a recipe in any day and meal (breakfast, lunch, dinner) with its own number of servings.
- **Shopping list**: scales every planned recipe to its servings, converts units and merges the same ingredient across recipes (e.g. 500 g + 1 kg flour → 1.5 kg). Units of different kinds (e.g. `pcs` and `g`) are kept as separate lines, and `pcs` are rounded up.

The planner only gets recipe data through `recipes/service.py`. A test (`test_planner_only_uses_recipes_service`) fails if the planner imports anything else from the recipes domain.

## Requirements

- Python 3.10 or newer
- No external services: everything runs in one process with a local SQLite file.

## Setup and run

```bash
git clone <repository-url>
cd <repository-folder>

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py
```

Then open http://localhost:8000.

The database and its tables are created automatically on the first start. There is no manual setup or migration step.

## Configuration

Everything is configured through environment variables. No `.env` file is required.

| Variable   | Default                     | Purpose                               |
| ---------- | --------------------------- | ------------------------------------- |
| `PORT`     | `8000`                      | Port the server listens on            |
| `DATA_DIR` | `./data` (next to `app.py`) | Folder that holds the SQLite database |

- The database file is always `$DATA_DIR/mealplanner.db`.
- The server binds to `0.0.0.0`, so it is reachable from outside a container.
- `GET /health` returns `{"status": "ok"}` once the app and database are ready.

Example with custom values:

```bash
PORT=9000 DATA_DIR=/tmp/mealplanner-data python app.py
```

## Tests and coverage

Run the full test suite with coverage of the two feature domains (the core business logic):

```bash
python -m pytest --cov=recipes --cov=planner --cov-report=term-missing
```

Result at submission:

```
107 passed
TOTAL                     340      1    99%
```

| Module                                                        | Coverage         |
| ------------------------------------------------------------- | ---------------- |
| `recipes/` (validation, repository, scaling, service, routes) | 98–100% per file |
| `planner/` (validation, repository, units, shopping, routes)  | 100% per file    |

Tests use a temporary SQLite file for each test, so they never touch your real data. See `ADR.md` entry 4 for the testing approach.

## Project structure

```
app.py              entry point: create_app(), registers both domains, /health
config.py           PORT, DATA_DIR and DB_PATH from environment variables
db.py               SQLite connection per request, schema created at startup
schema.sql          all tables (recipes domain + planner domain)

recipes/            domain 1
  validation.py     parses and validates recipe forms ("200 g flour")
  repository.py     all SQL for recipes and ingredients
  scaling.py        scales ingredient quantities to a number of servings
  service.py        the ONLY entry point other domains may use
  routes.py         recipe pages

planner/            domain 2
  validation.py     validates plan and meal-entry forms
  repository.py     all SQL for meal plans and entries
  units.py          unit families and conversion (g <-> kg, ml <-> l, tsp/tbsp -> ml)
  shopping.py       builds the merged shopping list
  routes.py         plan pages and shopping list page

templates/          Jinja HTML templates
tests/              pytest tests for both domains
ADR.md              architecture decision records
AI_USAGE.md         log of AI assistance
```

## Database

Five tables in one SQLite file:

- **Recipes domain:** `recipes`, `ingredients`, `recipe_ingredients`
- **Planner domain:** `meal_plans`, `plan_entries`

`plan_entries.recipe_id` refers to a recipe **without a foreign key** on purpose, so the two domains could later have separate databases. A recipe deleted after being planned shows as "(deleted recipe)" and is left out of the shopping list. See `ADR.md` entries 2 and 3.

## Known limitations

- `tsp` and `tbsp` are shown as `ml` on the shopping list.
- Case-insensitive matching only covers A–Z, so "Ñame" and "ñame" count as different ingredients.
- Ingredients no longer used by any recipe are not cleaned up.
- There is no login: anyone with access can edit any recipe or plan (`ADR.md` entry 5).
