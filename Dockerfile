# 1) Build frontendu (React/Vite) -> frontend/dist
FROM node:24-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Aplikacja Django
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Czcionki z polskimi znakami do generowania PDF
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY --from=frontend /build/dist /app/frontend/dist
RUN chmod +x /app/entrypoint.sh

RUN useradd --system --uid 1000 --create-home app && mkdir -p /app/public && chown -R app /app/public
USER app

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "kompetiq.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--worker-class", "gthread", "--threads", "8", "--timeout", "180", "--access-logfile", "-"]
