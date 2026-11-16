-- Planner service schema: only the planner domain's tables.
-- Runs at every startup, so every statement uses IF NOT EXISTS.
-- (Replaced by versioned migrations in the SQL Server step.)

CREATE TABLE IF NOT EXISTS meal_plans (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    week_start TEXT NOT NULL,  -- ISO date of the week's Monday, e.g. '2026-10-05'
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_entries (
    id        INTEGER PRIMARY KEY,
    plan_id   INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    day       TEXT    NOT NULL CHECK (day IN ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')),
    meal_slot TEXT    NOT NULL CHECK (meal_slot IN ('breakfast', 'lunch', 'dinner')),
    recipe_id INTEGER NOT NULL,  -- id of a recipe in the RECIPES service: no foreign key possible across databases
    servings  INTEGER NOT NULL CHECK (servings > 0),
    UNIQUE (plan_id, day, meal_slot)  -- one recipe per meal slot
);