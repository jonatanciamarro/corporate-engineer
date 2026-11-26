"""
tests/test_hook_resilience_and_rule_triggers.py - Shift-Left TDD Test Suite for IMP-0028 / ADR-027.
Validates that:
1. All rules in .agents/rules/ possess valid trigger frontmatter (especially corp-pipeline-orchestrator.md).
2. The universal hook launcher run_hook.py resolves .venv and script paths cleanly from any CWD.
3. .agents/hooks.json utilizes run_hook.py across all lifecycle events.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = WORKSPACE_ROOT / ".agents" / "rules"
HOOKS_DIR = WORKSPACE_ROOT / ".agents" / "orchestration" / "hooks"
HOOKS_JSON = WORKSPACE_ROOT / ".agents" / "hooks.json"
RUN_HOOK_SCRIPT = HOOKS_DIR / "run_hook.py"


def test_all_rules_have_valid_trigger_frontmatter():
    """Verify that every rule file in .agents/rules/ has YAML frontmatter with a trigger."""
    assert RULES_DIR.exists(), f"Rules directory not found: {RULES_DIR}"
    rule_files = list(RULES_DIR.glob("*.md"))
    assert len(rule_files) > 0, "No rule files found in .agents/rules/"

    missing_trigger = []
    for rule in rule_files:
        content = rule.read_text(encoding="utf-8", errors="ignore")
        match = re.match(r"^---\s*[\r\n]+([\s\S]*?)[\r\n]+---", content)
        if not match:
            missing_trigger.append(f"{rule.name} (NO FRONTMATTER)")
            continue
        frontmatter = match.group(1)
        if "trigger:" not in frontmatter:
            missing_trigger.append(f"{rule.name} (MISSING trigger:)")

    assert not missing_trigger, f"Rule files missing trigger frontmatter: {missing_trigger}"


def test_corp_pipeline_orchestrator_has_always_on():
    """Verify specifically that corp-pipeline-orchestrator.md has trigger: always_on."""
    rule_file = RULES_DIR / "corp-pipeline-orchestrator.md"
    assert rule_file.exists(), "corp-pipeline-orchestrator.md does not exist"
    content = rule_file.read_text(encoding="utf-8", errors="ignore")
    match = re.match(r"^---\s*[\r\n]+([\s\S]*?)[\r\n]+---", content)
    assert match is not None, "corp-pipeline-orchestrator.md has no YAML frontmatter"
    frontmatter = match.group(1)
    assert "trigger: always_on" in frontmatter, (
        "corp-pipeline-orchestrator.md must have trigger: always_on"
    )


def test_run_hook_script_exists():
    """Verify that run_hook.py exists in .agents/orchestration/hooks/."""
    assert RUN_HOOK_SCRIPT.exists(), f"Missing universal hook launcher: {RUN_HOOK_SCRIPT}"


def test_run_hook_executes_proactive_advisor():
    """Test executing run_hook.py with proactive_advisor from workspace root."""
    if not RUN_HOOK_SCRIPT.exists():
        pytest.fail("run_hook.py does not exist yet")

    payload = json.dumps({"lastUserInput": "teste de tdd proativo"})
    proc = subprocess.run(
        [sys.executable, str(RUN_HOOK_SCRIPT), "proactive_advisor"],
        check=False,
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
        timeout=15,
    )
    assert proc.returncode == 0, (
        f"run_hook.py failed with returncode {proc.returncode}: {proc.stderr}"
    )
    data = json.loads(proc.stdout)
    assert "injectSteps" in data
    assert len(data["injectSteps"]) > 0
    assert "systemMessage" in data["injectSteps"][0]


def test_run_hook_executes_security_guard():
    """Test executing run_hook.py with pre_tool_security_guard from workspace root."""
    if not RUN_HOOK_SCRIPT.exists():
        pytest.fail("run_hook.py does not exist yet")

    payload = json.dumps(
        {
            "toolCall": {
                "name": "write_file",
                "args": {"Path": "test_clean.py", "Content": "print('hello world')"},
            }
        }
    )
    proc = subprocess.run(
        [sys.executable, str(RUN_HOOK_SCRIPT), "pre_tool_security_guard"],
        check=False,
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
        timeout=15,
    )
    assert proc.returncode == 0, f"run_hook.py failed: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data.get("decision") in ("allow", "ask", "deny")


def test_hooks_json_configured_with_run_hook():
    """Verify that .agents/hooks.json points to run_hook.py across lifecycle events."""
    assert HOOKS_JSON.exists(), f"Missing hooks.json: {HOOKS_JSON}"
    content = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    orchestrator_config = content.get("corp-pipeline-orchestrator", {})
    assert orchestrator_config.get("enabled") is True

    # Check that commands reference run_hook.py
    session_start = orchestrator_config.get("SessionStart", [])
    assert len(session_start) > 0
    assert "run_hook.py" in session_start[0].get("command", "")

    pre_invocation = orchestrator_config.get("PreInvocation", [])
    assert len(pre_invocation) > 0
    assert "run_hook.py" in pre_invocation[0].get("command", "")


def _load_run_hook_module():
    """Load .agents/orchestration/hooks/run_hook.py dynamically for unit tests."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_hook_under_test", RUN_HOOK_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_hook_dynamic_discovery_with_function(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Any <hook_name>.py in hooks dir with run_<hook_name>_hook() should be discovered."""
    hooks_dir = tmp_path / ".agents" / "orchestration" / "hooks"
    hooks_dir.mkdir(parents=True)
    custom_hook = hooks_dir / "sample_custom.py"
    custom_hook.write_text(
        'def run_sample_custom_hook() -> None:\n    print(\'{"status": "custom_fn_ok"}\')\n',
        encoding="utf-8",
    )

    run_hook_mod = _load_run_hook_module()
    ret = run_hook_mod.run_in_process("sample_custom", tmp_path)
    captured = capsys.readouterr()

    assert ret == 0
    assert json.loads(captured.out.strip()) == {"status": "custom_fn_ok"}


def test_run_hook_dynamic_discovery_main_fallback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Hooks without run_<hook_name>_hook() should execute via __main__ fallback."""
    hooks_dir = tmp_path / ".agents" / "orchestration" / "hooks"
    hooks_dir.mkdir(parents=True)
    script_hook = hooks_dir / "script_only_hook.py"
    script_hook.write_text(
        'if __name__ == "__main__":\n    print(\'{"status": "main_fallback_ok"}\')\n',
        encoding="utf-8",
    )

    run_hook_mod = _load_run_hook_module()
    ret = run_hook_mod.run_in_process("script_only_hook", tmp_path)
    captured = capsys.readouterr()

    assert ret == 0
    assert json.loads(captured.out.strip()) == {"status": "main_fallback_ok"}


@pytest.mark.parametrize(
    "bad_name",
    [
        "../evil",
        "../../etc/passwd",
        "sub/hook",
        "sub\\hook",
        "hook;whoami",
        "hook.other",
        "",
    ],
)
def test_run_hook_blocks_path_traversal_and_invalid_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad_name: str
) -> None:
    """Strict regex validation must block path traversal and invalid hook names."""
    orchestration_dir = tmp_path / ".agents" / "orchestration"
    hooks_dir = orchestration_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    marker = tmp_path / "pwned.txt"
    (orchestration_dir / "evil.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwned', encoding='utf-8')\n",
        encoding="utf-8",
    )

    run_hook_mod = _load_run_hook_module()
    ret = run_hook_mod.run_in_process(bad_name, tmp_path)
    captured = capsys.readouterr()

    assert ret == 1
    assert not marker.exists()
    assert captured.err.strip() != ""
