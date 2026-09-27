"""All runtime configuration, read from environment variables (contract §7.3, §7.5, §7.9)."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Port to listen on. Default 8000 (5000 clashes with AirPlay on macOS).
PORT = int(os.environ.get("PORT", "8000"))

# Folder that holds the SQLite file. Default: ./data next to this file.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))

# The one documented SQLite path.
DB_PATH = os.path.join(DATA_DIR, "mealplanner.db")
