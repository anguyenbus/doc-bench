.PHONY: install lint format test test-build test-cov eval-parsing eval-rag regen-fixtures clean ci

# Default target
all: install lint test

# Install dependencies using uv
install:
	uv sync

# Run linting (ruff)
lint:
	uv run ruff check .
	uv run black --check .

# Format code with black and ruff
format:
	uv run ruff format .
	uv run black .

# Run type checking with mypy
typecheck:
	uv run mypy src

# Run tests
test:
	uv run pytest -q

# Run the marked wheel-build leak guard (deselected from the default fast loop).
# Builds the wheel and asserts ZERO docling_baseline paths leak into the artifact.
# NOTE: scoped to the guard's own test file so pre-existing collection errors in
# unrelated modules cannot abort the marker selection before this guard runs.
test-build:
	uv run pytest -m build tests/test_wheel_no_generator_leak.py

# Run tests with coverage report
test-cov:
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# Run parsing evaluation (stub parser by default)
eval-parsing:
	uv run eval-parsing --dataset omnidocbench --parser stub

# Run RAG evaluation (stub RAG by default)
eval-rag:
	uv run eval-rag --dataset legalbench_rag --slice mini --rag stub

# Regenerate DP-Bench and OmniDocBench baseline fixtures in-place.
# Runs the vendored generator under the dev-only `generator` group on Python
# 3.13 (uv auto-provisions it; doc-bench core stays requires-python >=3.12).
# Override a single dataset with DATASET=, e.g.:
#   make regen-fixtures DATASET=dp_bench
regen-fixtures:
	DATASET="$(DATASET)" uv run --python 3.13 --group generator python scripts/regenerate_fixtures.py

# Clean generated files
clean:
	rm -rf results/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run pre-commit checks (CI simulation).
# `test` runs the fast suite (which includes the byte-equality drift guard,
# tests/test_metric_drift_guard.py); `test-build` runs the marked wheel-leak
# guard that is deselected from the default fast loop.
ci: install lint typecheck test test-build
