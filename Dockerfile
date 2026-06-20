# --- Stage 1: Build dependencies ---
FROM python:3.12-slim-bookworm AS builder
WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Use a virtual environment so we can copy it cleanly into the runtime stage
RUN python -m venv /opt/venv

COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    APP_ENV=production

# Runtime libs needed by reportlab / Pillow / qrbill
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libfreetype6 libjpeg62-turbo \
        fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

EXPOSE 3001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
