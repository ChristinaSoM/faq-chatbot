FROM python:3.14-slim AS builder

# Prevent Python from writing .pyc files (keeps image clean)
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure stdout/stderr are unbuffered (better logging in containers)
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
# --no-install-project: only install dependencies, not the project itself
# (src/ is not present in the builder stage, so the project can't be built here)
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# VIRTUAL_ENV tells Python to activate the venv and use its site-packages
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create a non-root user for better security
RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /app/.venv /app/.venv

# Copy application source code and data
COPY src/ ./src/
COPY data/ ./data/

# Change ownership of files to non-root user
RUN chown -R appuser:appuser /app
# Switch to non-root user for execution (security best practice)
USER appuser

ENTRYPOINT ["python", "src/chatbot.py"]
