# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 – builder: compile any C-extension wheels (cffi, cryptography, etc.)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# Install into an isolated prefix so they can be copied cleanly to the
# runtime image without pulling in the build tools.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 – runtime: lean image with only what is needed to run the app
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user for security
RUN useradd --create-home --shell /bin/bash hrms

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application source (excludes everything in .dockerignore)
COPY . .

# Ensure the uploads directory exists and is writable by the app user
RUN mkdir -p app/uploads/avatars \
    && chown -R hrms:hrms /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER hrms

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
