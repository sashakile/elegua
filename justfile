# Eleguá development commands

# Install dependencies and set up git hooks
setup:
    uv sync --group docs
    vale sync
    git config core.hooksPath .hooks
    @echo "✓ Dependencies installed, git hooks configured"

# Run all pre-commit checks (lint, format, typecheck, typos, vale)
check:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    uv run pyright src/
    typos
    vale docs/ src/ tests/ README.md

# Auto-fix lint and format issues
fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run tests
test *args:
    uv run pytest {{ args }}

# Run tests with coverage
cov:
    uv run pytest --cov=elegua --cov-report=term-missing

# Run the full CI pipeline locally
ci: check test

# Lint only (ruff)
lint:
    uv run ruff check src/ tests/

# Format only (ruff)
fmt:
    uv run ruff format src/ tests/

# Typecheck only (pyright)
typecheck:
    uv run pyright src/

# Serve docs locally
docs-serve:
    uv run --group docs mkdocs serve

# Build docs to site/
docs-build:
    uv run --group docs mkdocs build --strict

# Deploy docs to GitHub Pages
docs-deploy:
    uv run --group docs mkdocs gh-deploy --force
