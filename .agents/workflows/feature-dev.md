---
description: Guided feature development with codebase understanding, Antigravity subagents, and architecture focus
---

# Feature Development Workflow

A structured feature-development workflow aligned with `corporate-engineer` and Antigravity native subagents (`research`, `self`, `swarm`).

## Phases

### 1. Discovery & Context Recovery

- Read `state.md` to restore active project state and constraints
- Read the feature request carefully; clarify requirements, constraints, and acceptance criteria
- Optionally run `.venv\Scripts\python -m corporate_engineer.cli prompt refine "<feature>"` or `anticipate "<feature>"`

### 2. Codebase Exploration

- Use the Antigravity native `research` subagent (read-only) to analyze existing code, execution paths, and integration points
- Inspect symbols and impact via MCP tools (`ast_symbols`, `blast_radius`) or CLI:
  ```powershell
  .venv\Scripts\python -m corporate_engineer.cli index src/corporate_engineer --format json
  .venv\Scripts\python -m corporate_engineer.cli blast-radius <target_path> --format json
  ```

### 3. Clarifying Questions

- Present findings from exploration
- Ask targeted design and edge-case questions (`ask_question` or `/grill-me_v2`)
- Wait for user response before proceeding

### 4. Architecture Design (Gate 1)

- Use `self` (applying `.agents/agents/architect.md` persona and `plan_v2` skill) to design the feature, Pydantic v2 `_FrozenDTO` contracts, and ADR in `docs/adr/`
- Verify all 5 auto-wiring links (DTOs, `__all__`, CLI `parser.py`/`main.py`, `PromptRefiner.DOMAIN_KEYWORDS`, `tests/`)
- Wait for user approval (**Gate 1**) before implementing

### 5. Shift-Left TDD Implementation

- Write failing tests in `tests/` first (RED), verify failure with `.venv\Scripts\pytest`
- Implement minimal surgical changes in `src/` to pass tests (GREEN)
- Ensure refactoring preserves immutability, strict typing, and test coverage (`>=80%`)

### 6. Quality Review & Pre-Flight

- Use `self` or `swarm` (applying `.agents/agents/code-reviewer.md`, `.agents/agents/python-reviewer.md`, and `.agents/agents/security-reviewer.md` personas) to review the diff
- Run MCP tools (`eval_scorecard`, `audit_wiring`, `secret_scan`) and `/preflight` (`pytest`, `ruff`, `mypy`, `secret_scanner.py`, `audit --wiring`)
- Address all CRITICAL/HIGH findings

### 7. Summary & Delivery (Gate 2)

- Update `state.md`, draft `docs/pull_requests/PR-CORP-xxx.md`, push branch (`git push -u origin <branch>`) before generating any PR link, and summarize verified results
