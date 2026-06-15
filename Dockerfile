FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MAF_LAB_HOST=0.0.0.0 \
    MAF_LAB_PORT=8000 \
    MAF_LAB_DATA_DIR=/app/data

WORKDIR /app

COPY pyproject.toml README.md requirements-lock.txt ./
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-lock.txt \
    && python -m pip install --no-cache-dir . --no-deps

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["maf-lab"]
