web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 1 --worker-class sync --timeout 120 --max-requests 100 --max-requests-jitter 10 --log-level error --preload
