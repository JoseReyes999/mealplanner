CREATE TABLE IF NOT EXISTS recipes (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  base_servings INTEGER NOT NULL CHECK (base_servings > 0),
  instructions TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
  recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  quantity REAL NOT NULL CHECK (quantity > 0),
  unit TEXT NOT NULL CHECK (unit IN ('g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'pcs')),
  PRIMARY KEY (recipe_id, ingredient_id)
);


-- ===== Planner domain =====
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
    recipe_id INTEGER NOT NULL,  -- soft reference to recipes(id): no FOREIGN KEY on purpose (ADR-2)
    servings  INTEGER NOT NULL CHECK (servings > 0),
    UNIQUE (plan_id, day, meal_slot)  -- one recipe per meal slot
);