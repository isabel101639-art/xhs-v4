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
    && pip install -r /app/requirements.txt \
    && useradd --create-home --shell /bin/sh appuser

COPY . /app

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8081

CMD ["python", "-m", "uvicorn", "crawler_service.main:app", "--host", "0.0.0.0", "--port", "8081"]
