-- 001: the planner service's first schema. Same tables as Assignment 1, in SQL Server syntax.
-- Never edit this file once it has run on Azure: change the schema with a new 002_... file.

CREATE TABLE meal_plans (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    name NVARCHAR(200) NOT NULL,
    week_start DATE NOT NULL,  -- the week's Monday
    created_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE plan_entries (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    plan_id INT NOT NULL REFERENCES meal_plans (id) ON DELETE CASCADE,
    day NVARCHAR(10) NOT NULL CHECK (day IN ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')),
    meal_slot NVARCHAR(10) NOT NULL CHECK (meal_slot IN ('breakfast', 'lunch', 'dinner')),
    -- id of a recipe in the RECIPES service's database: a soft reference, no foreign key
    -- is possible across databases. The planner checks it over HTTP before saving.
    recipe_id INT NOT NULL,
    servings INT NOT NULL CHECK (servings > 0),
    CONSTRAINT uq_plan_entries_slot UNIQUE (plan_id, day, meal_slot)  -- one recipe per meal slot
);