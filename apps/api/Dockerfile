FROM python:3.13-slim
WORKDIR /app
COPY apps/api/pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py
RUN pip install --no-cache-dir .
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./
COPY data /data
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
