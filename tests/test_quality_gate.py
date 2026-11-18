from pathlib import Path

from corporate_engineer.quality.gate import QualityGateRunner


def test_quality_gate_clean_dir(tmp_path: Path):
    runner = QualityGateRunner(project_root=tmp_path)
    res = runner.run_secret_scan()
    assert res["passed"] is True
    assert len(res["findings"]) == 0


def test_quality_gate_catches_secret(tmp_path: Path):
    dirty_file = tmp_path / "config.py"
    # Construct synthetic key dynamically so scanner doesn't trip on test suite itself
    prefix = "sk-proj-"
    suffix = "12345678901234567890123456789012"
    dirty_file.write_text(f"OPENAI_KEY = '{prefix}{suffix}'\n", encoding="utf-8")

    runner = QualityGateRunner(project_root=tmp_path)
    res = runner.run_secret_scan()
    assert res["passed"] is False
    assert len(res["findings"]) > 0
    assert any("OpenAI API Key" in str(f) for f in res["findings"])
