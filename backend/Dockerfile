FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY agropolia ./agropolia
RUN pip install --no-cache-dir .
CMD ["uvicorn", "agropolia.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
