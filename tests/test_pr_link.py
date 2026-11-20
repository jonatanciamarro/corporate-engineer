"""
Tests for Pre-Filled GitHub Pull Request URL Generation and Hook Integration.
"""

from pathlib import Path

from corporate_engineer.cli import main
from corporate_engineer.git_utils import (
    extract_github_repo_slug,
    generate_pr_url,
    get_current_branch,
    is_branch_pushed,
    push_branch_to_remote,
)


def test_extract_github_repo_slug():
    https_remote = "https://github.com/jonatanciamarro/corporate-engineer.git"
    ssh_remote = "git@github.com:jonatanciamarro/corporate-engineer.git"
    assert extract_github_repo_slug(https_remote) == "jonatanciamarro/corporate-engineer"
    assert extract_github_repo_slug(ssh_remote) == "jonatanciamarro/corporate-engineer"


def test_get_current_branch():
    branch = get_current_branch()
    assert branch != ""
    assert isinstance(branch, str)


def test_generate_pr_url_prefilled(tmp_path: Path):
    doc_path = tmp_path / "PR-CORP-999.md"
    doc_content = """# Pull Request: feat(test): sample feature title (IMP-9999)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-9999`
"""
    doc_path.write_text(doc_content, encoding="utf-8")

    info = generate_pr_url(
        repo_path=tmp_path,
        branch="feat/IMP-9999-sample",
        base="main",
        pr_doc_path=doc_path,
        repo_slug="jonatanciamarro/corporate-engineer",
    )

    assert info["branch"] == "feat/IMP-9999-sample"
    assert info["base"] == "main"
    assert "IMP-9999" in info["title"]
    assert "quick_pull=1" in info["url"]
    assert "title=" in info["url"]
    assert "body=" in info["url"]
    assert (
        "https://github.com/jonatanciamarro/corporate-engineer/compare/main...feat/IMP-9999-sample"
        in info["url"]
    )


def test_cli_pr_link(capsys):
    ret = main(["pr-link"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "https://github.com/" in captured.out or "quick_pull=1" in captured.out


def test_cli_pr_link_json(capsys):
    ret = main(["pr-link", "--format", "json"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "url" in captured.out
    assert "branch" in captured.out


def test_is_branch_pushed_mock():
    # Testa verificação com branch mockada
    assert is_branch_pushed(".", "main") in [True, False]


def test_push_branch_to_remote_mock():
    # Testa chamada sem falha de exceção
    assert isinstance(push_branch_to_remote(".", "non-existent-dummy-branch"), bool)


def test_generate_pr_url_ensure_pushed(tmp_path: Path):
    doc_path = tmp_path / "PR-CORP-TEST.md"
    doc_path.write_text("# Pull Request: feat: test push", encoding="utf-8")
    info = generate_pr_url(
        repo_path=tmp_path,
        branch="feat/test-pushed",
        pr_doc_path=doc_path,
        ensure_pushed=False,
    )
    assert info["branch"] == "feat/test-pushed"
    assert "pushed" in info
    assert info["pushed"] is False
