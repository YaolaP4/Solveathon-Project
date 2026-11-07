#!/bin/sh
set -e
cd /app
if [ "$MODE" = "job" ]; then
  exec python src/job.py
else
  exec gunicorn --chdir src --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 4 --timeout 120 \
       --access-logfile - webapp:app
fi
