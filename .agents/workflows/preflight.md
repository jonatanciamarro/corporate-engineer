---
description: Run full corporate pre-flight quality gate: Ruff, Mypy, Pytest and Secret Scanner
---
# Pre-Flight Verification Gate

Run the standard pre-flight audit for the `corporate-engineer` project.

## Verification Checklist

1. **Ruff Lint Check**:
   ```powershell
   ruff check .
   ```
2. **Mypy Type Check**:
   ```powershell
   mypy .
   ```
3. **Pytest Regression Suite**:
   ```powershell
   pytest -v
   ```
4. **Secret Scanner**:
   ```powershell
   python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
   ```

Verify all checks pass with 0 errors before staging or committing.
