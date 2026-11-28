---
description: Run the corporate-engineer static, formatting, AST scorecard, and auto-wiring quality gate.
---

# Quality Gate Command

Run the `corporate-engineer` quality gate using the project's real CLI, MCP tools, and Antigravity lifecycle hooks.

## Deterministic Tools & Hooks

1. **Strict Pre-Flight & Wiring Gate (CLI)**:
   ```powershell
   .venv\Scripts\python -m corporate_engineer.cli audit --strict --wiring --format json
   ```
2. **Semantic AST Scorecard (CLI or MCP)**:
   ```powershell
   .venv\Scripts\python -m corporate_engineer.cli eval --path src/ --format json
   ```
   Or invoke MCP tool `eval_scorecard` / `audit_wiring` exposed by `.agents/plugins/corporate-engineer/mcp_config.json`.
3. **Formatting, Lint, Type Check & Secret Scan**:
   ```powershell
   .venv\Scripts\ruff format --check .
   .venv\Scripts\ruff check .
   .venv\Scripts\mypy .
   .venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
   ```
4. **Automated PostToolUse Hook**:
   When the workspace is trusted in Antigravity, `.agents/hooks.json` invokes `.agents/orchestration/hooks/run_hook.py post_tool_auto_healer` after `write_file` / `edit_file` to run `ASTSelfHealingFixer`, `ruff format`, and `BlastRadiusAnalyzer` on modified `.py` files, and `pre_tool_security_guard` before writes.

## Auto-Remediation (Explicit Only)

To apply conservative AST self-healing and formatting fixes manually:

```powershell
.venv\Scripts\python -m corporate_engineer.cli fix --auto --path src/
.venv\Scripts\ruff format .
```

## Arguments

$ARGUMENTS:

- `[path]` optional target path to evaluate (defaults to `.` / `src/`).
