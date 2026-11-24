-- 001: the recipes service's first schema. Same tables as Assignment 1, in SQL Server syntax.
-- Never edit this file once it has run on Azure: change the schema with a new 002_... file.

CREATE TABLE recipes (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
    base_servings INT NOT NULL CHECK (base_servings > 0),
    instructions NVARCHAR(MAX) NULL,
    created_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);

-- A case-insensitive (CI) collation makes 'Flour' and 'flour' the same ingredient,
-- which is what COLLATE NOCASE did in SQLite.
CREATE TABLE ingredients (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    name NVARCHAR(200) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL UNIQUE
);

-- NO ACTION is SQL Server's RESTRICT: an ingredient used by a recipe can't be deleted.
CREATE TABLE recipe_ingredients (
    recipe_id INT NOT NULL REFERENCES recipes (id) ON DELETE CASCADE,
    ingredient_id INT NOT NULL REFERENCES ingredients (id) ON DELETE NO ACTION,
    quantity FLOAT NOT NULL CHECK (quantity > 0),
    unit NVARCHAR(10) NOT NULL CHECK (unit IN ('g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'pcs')),
    PRIMARY KEY (recipe_id, ingredient_id)
);