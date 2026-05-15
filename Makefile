SHELL = /bin/sh
PYTHON = python3

.PHONY: install test lint typecheck check clean build dev install-dev

install:
	$(PYTHON) -m pip install .

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	ruff check boxes/

typecheck:
	$(PYTHON) -m mypy boxes/ --no-error-summary

check: lint typecheck test

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/
	find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	$(PYTHON) -m build

dev: install-dev
install-dev:
	$(PYTHON) -m pip install -e ".[dev]"
