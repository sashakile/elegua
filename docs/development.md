# Development

## Setup

```bash
just setup
```

This runs `uv sync`, `vale sync`, and configures `git config core.hooksPath .hooks`.

## Commands

| Command | What it does |
|---------|-------------|
| `just setup` | Install deps, sync vale, configure hooks |
| `just check` | Run all checks (lint, format, typecheck, typos, vale) |
| `just fix` | Auto-fix lint and format issues |
| `just test` | Run tests (accepts args: `just test -v -k blob`) |
| `just cov` | Run tests with coverage report |
| `just ci` | Full local CI: check + test |
| `just lint` | ruff lint only |
| `just fmt` | ruff format only |
| `just typecheck` | pyright only |
| `just docs-serve` | Serve docs locally |
| `just docs-build` | Build docs to `site/` |
| `just docs-deploy` | Deploy docs to GitHub Pages |

## Git hooks

Hooks live in `.hooks/` (tracked in git). They are activated by `just setup` via `git config core.hooksPath .hooks`.

**Pre-commit** runs:

1. `ruff check` — lint (pycodestyle, pyflakes, isort, bugbear, and more)
2. `ruff format --check` — format verification
3. `pyright` — static type checking on `src/`
4. `typos` — spell checking
5. `vale` — prose linting on `src/`, `tests/`, `README.md`

**Pre-push** runs:

1. `pytest` — full test suite

## CI

GitHub Actions runs on push and PR to main:

- **lint** — ruff + pyright
- **typos** — spell check
- **vale** — prose lint
- **test** — pytest across Python 3.11, 3.12, 3.13

## Code style

- **Line length:** 100
- **Lint rules:** E, W, F, I, UP, B, SIM, RUF (see `pyproject.toml`)
- **Type checking:** pyright in standard mode
- **Enum style:** `StrEnum` (not `str, Enum`)
- **Immutability:** `model_copy(update={...})` instead of mutation

## Testing

- All code must have tests
- Target: 100% line coverage
- Tests use `pytest` with `pytest-cov`
- Edge cases and error paths must be covered
- Parametrize related cases (see `test_terminal_states_reject_all_transitions`)

## Adding a new module

1. Create `src/elegua/mymodule.py`
2. Create `tests/test_mymodule.py` with failing tests (red)
3. Implement until tests pass (green)
4. Run `just check` to verify lint, types, and prose
5. Run `just cov` to verify coverage stays at 100%
