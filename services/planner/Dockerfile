# Image for the planner service. Built by CI and pushed to GHCR tagged with the commit SHA.
FROM python:3.12-slim

# Print logs straight away (no buffering) and don't write .pyc files.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Don't run as root inside the container.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# gunicorn instead of Flask's development server, on $PORT (8000 if not set). One worker
# (migrations run at startup, so only one process may start the app) with 4 threads.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 'app:create_app()'"]