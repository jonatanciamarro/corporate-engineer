---
description: Create, verify, or list DAG and Git workflow checkpoints after running verification checks.
---

# Checkpoint Command

Inspect, create, or verify checkpoints in `corporate-engineer` using the DAG checkpoint engine (`.checkpoints/`) and Git state.

## Usage

`/checkpoint [create|verify|list] [name]`

## List DAG Checkpoints

Inspect FSM phases, transitions, and persisted DAG checkpoints:

```powershell
.venv\Scripts\python -m corporate_engineer.cli dag --show-phases --checkpoints --format json
```

To visualize the DAG topology as Mermaid:

```powershell
.venv\Scripts\python -m corporate_engineer.cli dag --mermaid
```

## Create Checkpoint

When creating a Git / state checkpoint:

1. Run `/preflight` (or `.venv\Scripts\python -m corporate_engineer.cli audit --strict --wiring`) to ensure current state is clean
2. Record progress in `state.md` (Section 2 & Section 5)
3. Create a clean commit or named Git stash:
   ```powershell
   git -c "safe.directory=*" status -s
   git -c "safe.directory=*" stash push -m "checkpoint: $CHECKPOINT_NAME"
   ```
4. Optionally run the autonomous pipeline checkpoint generator in dry-run simulation mode:
   ```powershell
   .venv\Scripts\python -m corporate_engineer.cli run --ticket CORP-CHK --task "$CHECKPOINT_NAME" --dry-run
   ```

## Verify Checkpoint

When verifying current state against baseline:

1. Check modified files and current tests/wiring:
   ```powershell
   git -c "safe.directory=*" diff --stat HEAD
   .venv\Scripts\pytest -q
   .venv\Scripts\python -m corporate_engineer.cli audit --wiring
   ```
2. Report:
   - Files changed
   - Pytest pass/fail summary
   - Ruff, Mypy, Secret Scan, and Wiring status

## Arguments

$ARGUMENTS:
- `create <name>` - Create named Git/DAG checkpoint after pre-flight checks
- `verify <name>` - Verify current workspace against clean pre-flight baseline
- `list` - List persisted DAG checkpoints via `corporate-engineer dag --checkpoints`
