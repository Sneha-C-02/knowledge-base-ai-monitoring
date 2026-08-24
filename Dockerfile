FROM python:3.11-slim as builder

WORKDIR /app

RUN pip install poetry==1.7.1
COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-root --only main

COPY . /app
RUN poetry install --no-interaction --no-ansi --only main

FROM python:3.11-slim as runtime

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 3000

CMD ["uvicorn", "src.knowledge_base_backend.main:app", "--host", "0.0.0.0", "--port", "3000"]
