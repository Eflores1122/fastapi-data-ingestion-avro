PYTHON ?= python3

.PHONY: install lint format test load run check

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check app tests scripts
	$(PYTHON) -m ruff format --check app tests scripts

format:
	$(PYTHON) -m ruff format app tests scripts

test:
	$(PYTHON) -m pytest

load:
	$(PYTHON) scripts/load_historical.py

run:
	$(PYTHON) -m uvicorn app.main:app --reload

check: lint test
