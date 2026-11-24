-- Creates one database per service, like on Azure (database-per-service), plus an
-- empty test database for each service's tests (the tests wipe it before every test).
-- The tables are not created here: each service creates its own with its migrations.
-- Safe to run again: it only creates what is missing.
IF DB_ID('recipes') IS NULL
    CREATE DATABASE recipes;
GO
IF DB_ID('planner') IS NULL
    CREATE DATABASE planner;
GO
IF DB_ID('recipes_test') IS NULL
    CREATE DATABASE recipes_test;
GO
IF DB_ID('planner_test') IS NULL
    CREATE DATABASE planner_test;
GO
SELECT name FROM sys.databases WHERE name IN ('recipes', 'planner', 'recipes_test', 'planner_test');
GO