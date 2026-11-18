-- Creates one database per service, like on Azure (database-per-service).
-- The tables are not created here: each service creates its own with its migrations.
-- Safe to run again: it only creates what is missing.
IF DB_ID('recipes') IS NULL
    CREATE DATABASE recipes;
GO
IF DB_ID('planner') IS NULL
    CREATE DATABASE planner;
GO
SELECT name FROM sys.databases WHERE name IN ('recipes', 'planner');
GO