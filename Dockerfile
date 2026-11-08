# One image, two roles (starter kit sec. 3):
#   MODE=app  -> the staff web app (gunicorn on port 8000)
#   MODE=job  -> the daily refresh pipeline; runs once and exits (non-zero on failure)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements-app.txt .
RUN pip install -r requirements-app.txt

COPY src/ src/
COPY agency/ agency/
COPY prompts/ prompts/
# USAspending responses cached during the qualifier: funder-history lookups start warm.
COPY data/cache/usaspending/ data/cache/usaspending/
COPY deploy/entrypoint.sh /entrypoint.sh

RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["sh", "/entrypoint.sh"]
