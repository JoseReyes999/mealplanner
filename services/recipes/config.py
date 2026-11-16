"""Recipes service configuration, read from environment variables."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Port to listen on. Each service runs in its own container, so both can use 8000.
PORT = int(os.environ.get("PORT", "8000"))

# Folder that holds this service's SQLite file (replaced by DATABASE_URL in the SQL Server step).
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "recipes.db")