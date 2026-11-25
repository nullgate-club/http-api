.PHONY: check format lint typecheck test build

check: lint typecheck test build

format:
	uv run --locked ruff format .
	uv run --locked ruff check --fix .

lint:
	uv run --locked ruff format --check .
	uv run --locked ruff check .

typecheck:
	uv run --locked mypy

test:
	uv run --locked pytest

build:
	uv build
