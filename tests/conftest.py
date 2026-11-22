"""
Pytest configuration and session fixtures for corporate-engineer test suite.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_git_safe_directory() -> None:
    """Ensure git commands within temporary directories pass dubious ownership checks."""
    gitconfig_path = (Path(__file__).parent.parent / ".gitconfig_sandbox").resolve()
    if not gitconfig_path.exists():
        gitconfig_path.write_text("[safe]\n\tdirectory = *\n", encoding="utf-8")
    os.environ["GIT_CONFIG_GLOBAL"] = str(gitconfig_path)
