# Agent Guidelines: Corporate Software Engineer

Repository-wide operating standards and instructions for AI agents working in `corporate-engineer`.

## Architecture & Codebase Map

- `src/corporate_engineer/models.py`: Strongly typed Pydantic v2 data models.
- `src/corporate_engineer/mcp/`: MCP client and protocol handling.
- `src/corporate_engineer/orchestrator/`: DAG orchestrator and graph runtime.
- `src/corporate_engineer/quality/`: Static and runtime quality enforcement.
- `src/corporate_engineer/rag/`: AST indexing and code intelligence.
- `src/corporate_engineer/cli.py`: CLI commands and argument parsing.
- `tests/`: Pytest suite and Hypothesis property-based tests.
- `docs/adr/`: Formal Architecture Decision Records (ADR).

## Commands

- Run Tests: `pytest`
- Run Coverage: `pytest --cov=src --cov-report=term-missing`
- Lint: `ruff check .`
- Format Check: `ruff format --check .`
- Type Check: `mypy .`
- Pre-Flight Secret Scanner: `python .agents/skills/corp-pipeline/scripts/secret_scanner.py .`

## Standards

1. Always read `state.md` at session start and update it before completing any session or work item.
2. Use TDD: write a failing test in `tests/` before modifying implementation in `src/`.
3. Follow PEP 8 and Python 3.11 idioms with explicit type hints everywhere.
4. Validate all data models using Pydantic v2 models.
5. Execute `/preflight` and verify 0 errors before submitting work.
6. Create an ADR in `docs/adr/` for significant architectural modifications.
7. Commit using Conventional Commits (`feat:`, `fix:`, `refactor:`, etc.).
