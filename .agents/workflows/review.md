---
description: Code review — local uncommitted changes or GitHub PR (pass PR number/URL for PR mode). Uses corporate-engineer CLI/MCP tools and Antigravity subagents.
argument-hint: "[pr-number | pr-url | blank for local review]"
---

# Code Review

**Input**: $ARGUMENTS

---

## Mode Selection

If `$ARGUMENTS` contains a PR number, PR URL, or `--pr`:
-> Jump to **PR Review Mode** below.

Otherwise:
-> Use **Local Review Mode**.

---

## Local Review Mode

Comprehensive security and quality review of uncommitted changes.

### Phase 1 — GATHER

```powershell
git -c "safe.directory=*" status -s
git -c "safe.directory=*" diff --name-only HEAD
```

If no changed files, stop: "Nothing to review."

### Phase 2 — REVIEW

Read each changed file in full (or inspect via Antigravity `research` / `self` subagent applying `.agents/agents/code-reviewer.md` and `.agents/agents/python-reviewer.md`). Also run deterministic analyzers:
- MCP tools: `eval_scorecard`, `blast_radius`, `audit_wiring`, `secret_scan`
- CLI checks: `.venv\Scripts\ruff check .`, `.venv\Scripts\mypy .`, `.venv\Scripts\pytest -q`

Check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- Command injection (`shell=True`) or SQL injection
- Missing input validation or path traversal risks
- Weakening MCP least-privilege defaults (`allow_mutations=False`)

**Code Quality (HIGH):**
- Functions > 50 lines or files > 800 lines
- Nesting depth > 4 levels
- Missing error handling or silent fallback swallowing
- Missing type hints or `Any` leaks in Pydantic v2 `_FrozenDTO` models
- Missing auto-wiring links (Invariante 9)

**Best Practices (MEDIUM):**
- In-place mutation of DTOs instead of `model_copy(update=...)`
- Missing Shift-Left TDD coverage for new behavior

### Phase 3 — REPORT

Generate report with:
- Severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
- Exact file path and line numbers
- Concrete failure mode and suggested fix

Block commit if `CRITICAL` or `HIGH` issues found.

---

## PR Review Mode

Comprehensive GitHub PR review — fetches diff, reads full files, runs validation, and reports findings.

### Phase 1 — FETCH

Parse input to determine PR:

| Input | Action |
|---|---|
| Number (e.g. `42`) | Use as PR number |
| URL (`github.com/.../pull/42`) | Extract PR number |
| Branch name | Find PR via `gh pr list --head <branch>` |

```powershell
gh pr view <NUMBER> --json number,title,body,author,baseRefName,headRefName,changedFiles,additions,deletions
gh pr diff <NUMBER>
```

If PR not found, stop with error.

### Phase 2 — CONTEXT

Build review context from canonical `corporate-engineer` sources:

1. **Project rules** — Read `AGENTS.md`, `GEMINI.md`, `state.md`, and `.agents/rules/`
2. **Architecture & PR docs** — Check `docs/adr/ADR-*.md` and `docs/pull_requests/PR-CORP-*.md`
3. **PR intent** — Parse PR description for goals, linked ticket (`IMP-xxxx`), and test plans
4. **Changed files** — List all modified files and inspect blast radius via `corporate-engineer blast-radius` or MCP `blast_radius`

### Phase 3 — REVIEW

Read each changed file **in full** and apply the review checklist across:
- **Correctness** (logic, edge cases, race conditions)
- **Type Safety** (`mypy .`, Pydantic v2 `_FrozenDTO` strictness)
- **Pattern Compliance** (`AGENTS.md`, immutability, Invariante 9 auto-wiring)
- **Security** (`secret_scanner.py`, path confinement, `shell=False`)
- **Completeness** (Shift-Left TDD tests, `state.md` & ADR updates)

Assign severity: `CRITICAL` (Block), `HIGH` (Request Changes), `MEDIUM` (Fix recommended), `LOW` (Optional).

### Phase 4 — VALIDATE

Run the full Python pre-flight gate:

```powershell
.venv\Scripts\pytest -q
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\mypy .
.venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
.venv\Scripts\python -m corporate_engineer.cli audit --wiring
```

### Phase 5 — DECIDE & REPORT

| Condition | Decision |
|---|---|
| Zero CRITICAL/HIGH issues, validation passes | **APPROVE** |
| Only MEDIUM/LOW issues, validation passes | **APPROVE** with comments |
| Any HIGH issues or validation failures | **REQUEST CHANGES** |
| Any CRITICAL issues | **BLOCK** — must fix before merge |

Save review report (when requested) in `docs/reviews/pr-<NUMBER>-review.md` or as an Antigravity artifact, and optionally publish via `gh pr review` after Gate 2 approval.
