.PHONY: help setup test test-all lint check-secrets hook docker-build docker-up docker-down clean

VENV ?= .venv
PYTHON ?= $(shell if [ -f $(VENV)/bin/python ]; then echo $(VENV)/bin/python; else echo python3; fi)
PIP ?= $(shell if [ -f $(VENV)/bin/pip ]; then echo $(VENV)/bin/pip; else echo pip3; fi)

help:
	@echo "PII Masking MVP - Development & Operational Workflows"
	@echo ""
	@echo "  make setup          Install dependencies into current Python environment"
	@echo "  make test           Run unit tests and verification suite"
	@echo "  make test-all       Run full test suite across modules"
	@echo "  make lint           Check code quality with ruff"
	@echo "  make check-secrets  Scan repository for uncommitted or leaked secrets"
	@echo "  make hook           Install git pre-commit hook for automatic secret scanning"
	@echo "  make docker-build   Build Docker container image"
	@echo "  make docker-up      Start API and worker services with Docker Compose"
	@echo "  make docker-down    Stop Docker Compose services"
	@echo "  make clean          Clean temporary files and test caches"

setup:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests/ evaluation/test_evaluation.py evaluation/test_vn_evaluation.py -v

test-all:
	$(PYTHON) -m pytest -v

lint:
	ruff check .

check-secrets:
	$(PYTHON) scripts/check_secrets.py --path .

hook:
	$(PYTHON) scripts/check_secrets.py --install-hook

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov dist build *.egg-info
