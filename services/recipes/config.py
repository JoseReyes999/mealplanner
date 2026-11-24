"""Recipes service configuration, read from environment variables."""
import os

# Port to listen on. Each service runs in its own container, so both can use 8000.
PORT = int(os.environ.get("PORT", "8000"))

# SQL Server connection: mssql://user:password@host:1433/database
# URL-encode special characters in the password (@ is %40). Add ?encrypt=require for Azure SQL.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# A paused Azure SQL serverless database takes about a minute to resume, so connecting
# is retried with a growing wait (1, 2, 4, 8, 15, 15... seconds).
DB_CONNECT_ATTEMPTS = int(os.environ.get("DB_CONNECT_ATTEMPTS", "8"))
DB_RETRY_MAX_WAIT_S = float(os.environ.get("DB_RETRY_MAX_WAIT_S", "15"))
DB_LOGIN_TIMEOUT_S = int(os.environ.get("DB_LOGIN_TIMEOUT_S", "15"))
DB_QUERY_TIMEOUT_S = int(os.environ.get("DB_QUERY_TIMEOUT_S", "30"))

# The only browser origin allowed to call this API (CORS). Locally the UI is served on
# port 8080; on Azure the pipeline sets this to the storage static website's URL.
UI_ORIGIN = os.environ.get("UI_ORIGIN", "http://localhost:8080")

# Which build is running, shown by /health. The pipeline sets it to the commit SHA.
VERSION = os.environ.get("APP_VERSION", "dev")
