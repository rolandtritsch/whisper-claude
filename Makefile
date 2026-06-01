# Whisper Wayland - Voice-to-Text Service Makefile

# Default target
.DEFAULT_GOAL := help

.PHONY: all
all: install check tests ## Run complete pipeline (install, check, test)
	@echo "🎉 Complete pipeline successful!"

.PHONY: check
check: format-check lint-check type-check ## Run all code quality checks
	@echo "✅ All code quality checks passed"

.PHONY: check-fix
check-fix: format-fix lint-fix type-check ## Run and fix all code quality checks
	@echo "✅ All code quality checks passed"

.PHONY: clean
clean: ## Clean up generated files and cache
	@echo "Cleaning up generated files..."
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov
	rm -rf whisper_wayland/__pycache__ tests/__pycache__
	rm -rf tests/unit/__pycache__ tests/integration/__pycache__
	rm -f .coverage transcription.txt
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "✅ Cleanup complete"

.PHONY: coverage
coverage: check ## Run tests with detailed coverage report
	@echo "Running tests with detailed coverage..."
	uv run pytest --cov=whisper_wayland --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "📊 Coverage report generated in htmlcov/"

.PHONY: format-check
format-check: ## Check code formatting with ruff
	@echo "Check code formatting with ruff..."
	uv run ruff format . --check
	@echo "✅ Code formatting complete"

.PHONY: format-fix
format-fix: ## Format code with ruff
	@echo "Formatting code with ruff..."
	uv run ruff format .
	@echo "✅ Code formatting complete"

.PHONY: help
help: ## Show available commands
	@echo "Whisper Wayland Development Commands"
	@echo "=================================="
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Available commands:\n"} \
		/^[a-zA-Z_-]+:.*##/ { \
			split($$1, target_parts, " "); \
			target = target_parts[1]; \
			gsub(/^[ \t]+|[ \t]+$$/, "", target); \
			printf "  %-15s %s\n", target, $$2 \
		}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment:"
	@echo "  Set WW_OPENAI_API_KEY environment variable for API tests"
	@echo "  Or create .env file with WW_OPENAI_API_KEY=your_key_here"

.PHONY: install
install: ## Install dependencies with uv
	@echo "Installing dependencies with uv..."
	uv sync

.PHONY: lint-check
lint-check: ## Check code linting with ruff
	@echo "Check code linting with ruff..."
	uv run ruff check .
	@echo "✅ Code linting complete"

.PHONY: lint-fix
lint-fix: ## Lint code with ruff (fix issues)
	@echo "Linting code with ruff..."
	uv run ruff check . --fix
	@echo "✅ Linting complete"

.PHONY: run
run: ## Run whisper-wayland service
	@echo "Starting whisper-wayland..."
	uv run whisper-wayland

.PHONY: run-debug
run-debug: ## Run whisper-wayland service with debug logging
	@echo "Starting whisper-wayland with debug logging..."
	WW_MIC_STARTUP_CHECK=auto WW_SUPPRESS_AUDIO_WARNINGS=false WW_LOG_LEVEL=DEBUG uv run whisper-wayland

.PHONY: tests
tests: tests-unit tests-integration ## Run all tests with coverage

.PHONY: tests-integration
tests-integration: ## Run only integration tests (requires WW_OPENAI_API_KEY)
	@echo "Running integration tests..."
	uv run pytest tests/integration -v

.PHONY: tests-unit
tests-unit: ## Run only unit tests
	@echo "Running unit tests..."
	uv run pytest tests/unit --cov=whisper_wayland --cov-report=term --cov-report=html --cov-fail-under=80 -v

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "Check type checks with mypy..."
	uv run mypy .
	@echo "✅ Type checking complete"
