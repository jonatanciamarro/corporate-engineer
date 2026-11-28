---
description: Run corporate-engineer security audit, secret scanning, and wiring/OWASP verification.
---

# Security Scan Command

Run deterministic secret scanning, static security checks, and workspace configuration auditing using `corporate-engineer` tools and Antigravity subagents (`self` / `research` applying `.agents/agents/security-reviewer.md`).

## Usage

`/security-scan [path]`

- `path` (optional): defaults to the workspace root (`.`).

## Deterministic Engines

1. **Canonical Secret Scanner (CLI & MCP)**:
   ```powershell
   .venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
   ```
   Or invoke the `secret_scan` MCP tool from `.agents/plugins/corporate-engineer/mcp_config.json` (which delegates to `CanonicalSecretScanner` and returns masked metadata only).

2. **Strict Quality & Wiring Audit**:
   ```powershell
   .venv\Scripts\python -m corporate_engineer.cli audit --strict --wiring --format json
   ```
   Or invoke `audit_wiring` via MCP.

3. **Zero-Secret PreToolUse Hook Verification**:
   Verify `.agents/hooks.json` (`pre_tool_security_guard` via `.agents/orchestration/hooks/run_hook.py`) is active when workspace is trusted.

Do not invent findings. Use tool outputs and actual file inspection as the source of truth.

## Review Checklist

1. Check active code and runtime surfaces:
   - Hardcoded secrets, API keys, tokens, private keys
   - Command injection (`shell=True` must not be used; verify `shlex.split` / `shell=False`)
   - Path traversal (`_resolve_safe_path()` confinement in MCP server / storage cleaner)
   - MCP servers least-privilege policy (`allow_mutations=False` default in `CorporateEngineerMCPServer`)
   - Untrusted workspace / hook execution boundaries
2. For each critical or high finding, report:
   - File path and line number
   - Severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
   - Concrete trigger/failure mode
   - Exact remediation

## Output Contract

Return:
1. Secret scanner status (`PASS` / `FAIL` and masked finding count).
2. Pre-flight & wiring audit status (`audit --strict --wiring`).
3. Critical/high findings with exact paths, or explicit confirmation of zero findings.
4. Remediation steps and commands executed.

## References

- Skill: `.agents/skills/security-scan/SKILL.md` and `.agents/skills/security-review/SKILL.md`
- Role Persona: `.agents/agents/security-reviewer.md` (used by `self` / `swarm`)
- Core Scanner: `src/corporate_engineer/quality/secret_scanner.py`
