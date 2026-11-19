import sys
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent / ".agents" / "skills" / "corp-pipeline" / "scripts"
)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import stack_detector  # type: ignore[import-not-found]


def test_detect_python_without_venv(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    result = stack_detector.detect_stack(tmp_path)

    assert result["stack"] == "python"
    assert result["package_manager"] == "pip/pyproject"
    assert "pytest" in result["test_cmd"]
    assert "ruff" in result["lint_cmd"]
    assert "mypy" in result["typecheck_cmd"]


def test_detect_python_with_windows_venv(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "pytest.exe").write_text("", encoding="utf-8")
    (scripts_dir / "ruff.exe").write_text("", encoding="utf-8")
    (scripts_dir / "mypy.exe").write_text("", encoding="utf-8")

    result = stack_detector.detect_stack(tmp_path)

    assert result["stack"] == "python"
    assert result.get("venv_detected") is True
    # The command should contain the path to the virtualenv executable
    assert ".venv" in result["test_cmd"]
    assert "pytest" in result["test_cmd"]
    assert ".venv" in result["lint_cmd"]
    assert "ruff" in result["lint_cmd"]
    assert ".venv" in result["typecheck_cmd"]
    assert "mypy" in result["typecheck_cmd"]


def test_detect_python_with_posix_venv(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "pytest").write_text("", encoding="utf-8")
    (bin_dir / "ruff").write_text("", encoding="utf-8")
    (bin_dir / "mypy").write_text("", encoding="utf-8")

    result = stack_detector.detect_stack(tmp_path)

    assert result["stack"] == "python"
    assert result.get("venv_detected") is True
    assert ".venv" in result["test_cmd"]
