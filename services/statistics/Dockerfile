# Build from the repository root with --platform linux/arm64 for the Pi.
FROM python:3.12-slim-bookworm

# Avoid bytecode files and send Python logs without buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only Statistics dependencies, without a database driver.
COPY services/statistics/requirements.txt ./requirements.txt
# Create a fixed non-root user without a home directory or login shell.
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

# Copy only Statistics code; Tasks is contacted through HTTP.
COPY services/statistics/app.py ./services/statistics/app.py

# Keep application files root-owned, but run the service as this user.
USER 10001:10001
# Document the internal port; this does not publish a host port.
EXPOSE 8000
# Check process health without requiring Tasks to be available.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; response = urlopen('http://127.0.0.1:8000/health', timeout=2); assert response.status == 200"]
# Use Gunicorn with two workers and two threads each, not the Flask dev server.
# Store worker temporary files in /tmp and send request/error logs to the console.
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "--threads=2", "--timeout=30", "--worker-tmp-dir=/tmp", "--access-logfile=-", "--error-logfile=-", "services.statistics.app:app"]