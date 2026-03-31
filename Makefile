.PHONY: run dev run-dev install

run:
	uv run uvicorn src.main:app --reload

dev: run

run-dev: run

install:
	uv sync
