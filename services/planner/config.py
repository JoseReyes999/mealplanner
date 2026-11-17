"""Planner service configuration, read from environment variables."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Port to listen on. Each service runs in its own container, so both can use 8000.
PORT = int(os.environ.get("PORT", "8000"))

# Folder that holds this service's SQLite file (replaced by DATABASE_URL in the SQL Server step).
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "planner.db")

# Where the recipes service lives. In docker compose the service is called "recipes";
# on Azure the pipeline sets this to the recipes Container App's HTTPS URL.
RECIPES_URL = os.environ.get("RECIPES_URL", "http://recipes:8000")

# Seconds to wait for the recipes service before giving up (every outbound call needs a timeout).
RECIPES_TIMEOUT_S = float(os.environ.get("RECIPES_TIMEOUT_S", "2"))