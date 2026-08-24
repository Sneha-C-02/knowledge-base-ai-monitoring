.PHONY: install run test coverage lint format type-check quality migrate create-user test-database

install:
	poetry install

run:
	poetry run uvicorn knowledge_base_backend.main:app --reload --host 0.0.0.0 --port 3000

test:
	poetry run pytest

coverage:
	poetry run pytest --cov=knowledge_base_backend

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

type-check:
	poetry run mypy src

quality: format lint type-check test

migrate:
	poetry run alembic upgrade head

create-user:
	poetry run python scripts/create_initial_user.py

test-database:
	poetry run python scripts/test_database_connection.py
