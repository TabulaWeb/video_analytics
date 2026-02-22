# Makefile for People Counter project
# Provides convenient commands for common tasks

.PHONY: help install check run test clean dev

help:  ## Show this help message
	@echo "People Counter - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

check:  ## Run system checks
	python check_system.py

run:  ## Run the application
	python run.py

dev:  ## Run in development mode (with reload)
	python run.py --reload

test:  ## Run tests
	pytest tests/ -v

test-counter:  ## Run counter self-check
	python -m app.counter

coverage:  ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:  ## Run linters
	flake8 app/ tests/ --max-line-length=100 --ignore=E203,W503
	@echo "✓ Linting passed"

format:  ## Format code with black
	black app/ tests/ --line-length=100
	@echo "✓ Code formatted"

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "✓ Cleaned up"

clean-db:  ## Delete database (WARNING: deletes all data)
	@read -p "Delete people_counter.db? [y/N] " confirm && [ "$$confirm" = "y" ] && rm -f people_counter.db && echo "✓ Database deleted" || echo "Cancelled"

venv:  ## Create virtual environment
	python3 -m venv .venv
	@echo "✓ Virtual environment created"
	@echo "Activate with: source .venv/bin/activate"

docker-build:  ## Build Docker image (if Dockerfile exists)
	@if [ -f Dockerfile ]; then \
		docker build -t people-counter:latest . ; \
		echo "✓ Docker image built"; \
	else \
		echo "❌ Dockerfile not found"; \
	fi

docker-run:  ## Run Docker container
	docker run --rm -it \
		--device=/dev/video0 \
		-p 8000:8000 \
		-e PC_SHOW_DEBUG_WINDOW=false \
		people-counter:latest

deps-tree:  ## Show dependency tree
	pip install pipdeptree
	pipdeptree

upgrade-deps:  ## Upgrade all dependencies
	pip install --upgrade -r requirements.txt
	@echo "✓ Dependencies upgraded"

.DEFAULT_GOAL := help
