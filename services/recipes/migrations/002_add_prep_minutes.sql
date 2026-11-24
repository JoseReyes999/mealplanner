-- 002: how many minutes a recipe takes to prepare.
-- Data-preserving: the column is added with a DEFAULT, so every existing recipe keeps all
-- its data and simply gets prep_minutes = 0. Nothing is dropped or renamed.
ALTER TABLE recipes
    ADD prep_minutes INT NOT NULL
        CONSTRAINT df_recipes_prep_minutes DEFAULT 0
        CONSTRAINT ck_recipes_prep_minutes CHECK (prep_minutes >= 0);