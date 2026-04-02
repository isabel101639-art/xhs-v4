FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/docker/entrypoint-web.sh /app/docker/entrypoint-worker.sh \
    && useradd --create-home --shell /bin/sh appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["./docker/entrypoint-web.sh"]
