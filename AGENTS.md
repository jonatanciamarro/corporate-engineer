# Agent Guidelines: Corporate Software Engineer & Corp-Pipeline Master Orchestrator

Repository-wide operating standards and instructions for AI agents working in `corporate-engineer`.

## Architecture & Codebase Map

- `src/corporate_engineer/models.py`: Strongly typed Pydantic v2 data models.
- `src/corporate_engineer/mcp/`: MCP client (stdio & SSE) and protocol handling.
- `src/corporate_engineer/orchestrator/`: DAG orchestrator, parallel execution, and graph runtime.
- `src/corporate_engineer/quality/`: Static and runtime quality enforcement (pre-flight).
- `src/corporate_engineer/rag/`: AST indexing and code intelligence (classes, inheritance, calls).
- `src/corporate_engineer/cli.py`: CLI commands (`audit`, `index`, `dag`, `mcp`).
- `tests/`: Pytest suite and Hypothesis property-based tests.
- `docs/adr/`: Formal Architecture Decision Records (ADR).
- `.agents/orchestration/`: Authoritative registries (capabilities, agents, skills, workflows, tools, integrations, improvement backlog).

## Commands (Recommended in Virtual Environment `.venv`)

- Run Tests: `.venv\Scripts\pytest` (or `pytest`)
- Run Coverage: `.venv\Scripts\pytest --cov=src --cov-report=term-missing`
- Lint: `.venv\Scripts\ruff check .`
- Format Check: `.venv\Scripts\ruff format --check .`
- Type Check: `.venv\Scripts\mypy .`
- Pre-Flight Secret Scanner: `.venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .`

## Standards & Operating Invariants

1. **Corp-Pipeline by Default**: All incoming tasks enter the Corp-Pipeline orchestration loop (Phases 0-6).
2. **State Tracking**: Always read `state.md` at session start and update it before completing any session or work item.
3. **Shift-Left TDD**: Write a failing test in `tests/` before modifying implementation in `src/`.
4. **Strict Typing & Pydantic v2**: Follow PEP 8 and Python 3.11 idioms with explicit type hints everywhere.
5. **Pre-Flight Mandatory**: Execute `/preflight` and verify 0 errors across all 4 checks before submitting work.
6. **Improvement Governance**: Never apply unsolicited architectural modifications. Present proposals via `[CORP-PIPELINE / IMPROVEMENT DETECTED]` and offer saving to `.agents/orchestration/improvement-backlog.md`.
7. **ADR & Git Conventions**: Create an ADR in `docs/adr/` for significant architectural modifications. Commit using Conventional Commits (`feat:`, `fix:`, `refactor:`, etc.).
8. **Mandatory Remote Push Before PR URL (Always-On)**: The agent must ALWAYS push the branch to `origin` (`git push -u origin <branch>`) BEFORE generating, presenting, or formatting the 1-click GitHub PR URL. A PR creation link must NEVER lead to a GitHub 404.
9. **Auto-Conexão e Potência Máxima Mandatória (Always-On Auto-Wiring)**: Toda nova implementação (módulo, classe, motor ou subcomando) DEVE OBRIGATORIAMENTE ser conectada aos 5 elos da cadeia: contratos Pydantic v2, exportação em `__all__`, exposição em subparser da CLI, mapeamento no Prompt Refiner e verificação no `QualityGateRunner.run_wiring_audit()`. Zero módulos órfãos ou desconectados são tolerados no repositório.


