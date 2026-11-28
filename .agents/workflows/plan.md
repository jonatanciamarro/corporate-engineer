---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code. Use for a single-model inline or ADR/plan_v2 implementation plan.
argument-hint: "[feature description | path/to/ADR-or-spec.md]"
---

# Plan Command

This command creates a comprehensive implementation plan before writing any code. It aligns with `plan_v2` and `docs/adr/` governance in `corporate-engineer`.

Run inline by default, or delegate exploration to the Antigravity native `research` subagent and isolated planning to `self` (applying the `.agents/agents/planner.md` or `.agents/agents/architect.md` persona when appropriate).

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built and check `state.md`
2. **Refine Prompt Context** - Optionally ground scope with `.venv\Scripts\python -m corporate_engineer.cli prompt refine "<request>"` or `.venv\Scripts\python -m corporate_engineer.cli anticipate "<request>"`
3. **Inspect Blast Radius & Symbols** - Use MCP tools `ast_symbols` and `blast_radius` (or `corporate-engineer index` / `blast-radius`)
4. **Create Step Plan & ADR** - Break down implementation into Shift-Left TDD phases, trade-offs, STRIDE threats, and Pydantic v2 `_FrozenDTO` contracts
5. **Wait for Confirmation (Gate 1)** - MUST receive user approval before proceeding

## When to Use

Use `/plan` when:
- Starting a new feature or architectural change
- Working on multi-module refactoring
- Multiple files/components will be affected
- Requirements are unclear or ambiguous

## Pattern Grounding

Before writing the plan, inspect the codebase (via `read_file` or native subagent `research`) for existing conventions:

| Category | What to capture |
|---|---|
| Naming | File, function, class, CLI command, or DTO naming in `src/corporate_engineer/` |
| Contracts | `_FrozenDTO` models in `src/corporate_engineer/models.py` |
| Auto-Wiring | Exports in `__all__`, CLI `parser.py`/`main.py`, `PromptRefiner.DOMAIN_KEYWORDS`, `tests/` |
| Error handling | Explicit failures, honest status flags, stderr logging |
| Tests | Shift-Left TDD suites in `tests/` (`pytest` + `hypothesis`) |

## Plan Artifact Output

For non-trivial architectural changes, store:
1. Formal ADR at `docs/adr/ADR-<NUM>-<slug>.md`
2. Detailed `plan_v2` artifact (`plan_v2_<slug>.md`) in the Antigravity artifact directory with:
   - Problem Statement & KPIs
   - Architecture Trade-off Matrix
   - Formal Pydantic v2 `_FrozenDTO` Contracts
   - STRIDE / OWASP Threat Model
   - Blast Radius & Rollback Strategy
   - Surgical Execution Waves (RED -> GREEN -> Pre-Flight)

After presenting the plan, **WAIT for explicit user confirmation** (`proceed` / `yes`) before modifying any code.

## Validation Commands

```powershell
.venv\Scripts\pytest -q
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\mypy .
.venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
.venv\Scripts\python -m corporate_engineer.cli audit --wiring
```

## Integration with Other Workflows

- Use `/plan_v2` and `/grill-me_v2` skills for interactive requirements discovery and ADR synthesis
- Use `/tdd-workflow` skill for Shift-Left RED -> GREEN -> IMPROVE execution
- Use `/preflight` and `/quality-gate` before committing
- Use `/review` for pre-PR code review and `docs/pull_requests/PR-CORP-xxx.md`

## Role Persona Reference

For structured planning checklists, consult the role persona template in `.agents/agents/planner.md` (run via `self` or inline; `.agents/agents/*.md` are prompt personas, not built-in `invoke_subagent` names).
