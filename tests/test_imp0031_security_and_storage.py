"""
Shift-Left TDD tests for IMP-0031:
1. CanonicalSecretScanner & synchronized fallback regex hardening (OpenAI / Anthropic keys).
2. SafeStorageCleaner.is_path_safe() & clean_target() defense-in-depth hardening.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from corporate_engineer.models import StorageTarget
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.quality.storage_cleaner import SafeStorageCleaner
from corporate_engineer.quality.tool_security_guard import evaluate_tool_security


def _make_openai_project_key() -> str:
    prefix = "sk-" + "proj-"
    body = "AbCd_1234-" * 3 + "EfGh_5678"
    return f"{prefix}{body}"


def _make_openai_svcacct_key() -> str:
    prefix = "sk-" + "svcacct-"
    body = "SvcAcct_90-" * 3 + "Zz12"
    return f"{prefix}{body}"


def _make_openai_live_key() -> str:
    prefix = "sk-" + "live-"
    body = "LiveKey_12-" * 3 + "Ab34"
    return f"{prefix}{body}"


def _make_anthropic_api03_key() -> str:
    prefix = "sk-" + "ant-api03-"
    body = "AntKey_1234-" * 3 + "AA"
    return f"{prefix}{body}"


def _make_anthropic_legacy_key() -> str:
    prefix = "sk-" + "ant-"
    body = "AntLegacy_56-" * 3 + "BB"
    return f"{prefix}{body}"


def _make_aws_long_key() -> str:
    prefix = "AKIA"
    body = "0123456789ABCDEF" + "GH"
    return f"{prefix}{body}"


def _load_module_isolated(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    file_path: Path,
    block_canonical: bool = False,
) -> ModuleType:
    if block_canonical:
        blocked: Any = cast(Any, None)
        monkeypatch.setitem(sys.modules, "corporate_engineer.quality.secret_scanner", blocked)
        monkeypatch.setitem(sys.modules, "corporate_engineer.quality", blocked)
        monkeypatch.setitem(sys.modules, "corporate_engineer", blocked)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============================================================================
# 1. Secret Scanner & Fallback Synchronization Tests
# ============================================================================


@pytest.mark.parametrize(
    "token_factory",
    [
        _make_openai_project_key,
        _make_openai_svcacct_key,
        _make_openai_live_key,
    ],
)
def test_secret_scanner_detects_modern_openai_keys(
    token_factory: Callable[[], str],
) -> None:
    scanner = CanonicalSecretScanner()
    token = token_factory()
    payload = f'OPENAI_CRED = "{token}"\n'

    findings = scanner.scan_text(payload, source_identifier="sample.py")

    assert len(findings) == 1
    assert findings[0]["rule_name"] == "OpenAI API Key"


@pytest.mark.parametrize(
    "token_factory",
    [
        _make_anthropic_api03_key,
        _make_anthropic_legacy_key,
    ],
)
def test_secret_scanner_detects_and_disambiguates_anthropic_keys(
    token_factory: Callable[[], str],
) -> None:
    scanner = CanonicalSecretScanner()
    token = token_factory()
    payload = f'ANTHROPIC_CRED = "{token}"\n'

    findings = scanner.scan_text(payload, source_identifier="sample.py")

    assert len(findings) == 1
    assert findings[0]["rule_name"] == "Anthropic API Key"


def test_secret_scanner_ignores_short_non_secret_prefixes() -> None:
    scanner = CanonicalSecretScanner()
    short_proj = "sk-" + "proj-" + "short123"
    short_ant = "sk-" + "ant-api03-" + "short123"
    payload = f'NOTE = "{short_proj} {short_ant}"\n'

    findings = scanner.scan_text(payload)
    assert findings == []


@pytest.mark.parametrize(
    ("token_factory", "expected_rule"),
    [
        (_make_openai_project_key, "OpenAI API Key"),
        (_make_openai_svcacct_key, "OpenAI API Key"),
        (_make_openai_live_key, "OpenAI API Key"),
        (_make_anthropic_api03_key, "Anthropic API Key"),
    ],
)
def test_tool_security_guard_denies_modern_keys(
    token_factory: Callable[[], str],
    expected_rule: str,
    tmp_path: Path,
) -> None:
    token = token_factory()
    payload = {
        "toolCall": {
            "name": "write_file",
            "args": {
                "Path": str(tmp_path / "settings.py"),
                "Content": f'PROVIDER_CRED = "{token}"\n',
            },
        }
    }

    decision = evaluate_tool_security(payload)

    assert decision["decision"] == "deny"
    assert expected_rule in decision["reason"]


def test_tool_security_guard_fallback_patterns_synchronized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    guard_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "corporate_engineer"
        / "quality"
        / "tool_security_guard.py"
    )
    mod = _load_module_isolated(
        monkeypatch,
        "isolated_tool_security_guard_fallback",
        guard_path,
        block_canonical=True,
    )

    for token, expected_rule in [
        (_make_openai_project_key(), "OpenAI API Key"),
        (_make_openai_svcacct_key(), "OpenAI API Key"),
        (_make_anthropic_api03_key(), "Anthropic API Key"),
        (_make_aws_long_key(), "AWS Access Key ID"),
    ]:
        decision = mod.evaluate_tool_security(
            {
                "toolCall": {
                    "name": "write_file",
                    "args": {
                        "Path": str(tmp_path / "cfg.py"),
                        "Content": f'CRED_VAL = "{token}"\n',
                    },
                }
            }
        )
        assert decision["decision"] == "deny"
        assert expected_rule in decision["reason"]


def test_corp_pipeline_script_secret_scanner_detects_modern_keys(tmp_path: Path) -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "corp-pipeline"
        / "scripts"
        / "secret_scanner.py"
    )
    spec = importlib.util.spec_from_file_location("corp_pipeline_secret_scanner", script_path)
    assert spec is not None and spec.loader is not None
    script_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script_mod)

    target_file = tmp_path / "leaked_keys.py"
    target_file.write_text(
        "\n".join(
            [
                f'OPENAI_A = "{_make_openai_project_key()}"',
                f'OPENAI_B = "{_make_openai_svcacct_key()}"',
                f'OPENAI_C = "{_make_openai_live_key()}"',
                f'ANTHROPIC_A = "{_make_anthropic_api03_key()}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    findings = script_mod.scan_file(target_file)
    rules = [rule_name for rule_name, _, _ in findings]

    assert rules == [
        "OpenAI API Key",
        "OpenAI API Key",
        "OpenAI API Key",
        "Anthropic API Key",
    ]


def test_corp_pipeline_script_fallback_patterns_synchronized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "corp-pipeline"
        / "scripts"
        / "secret_scanner.py"
    )
    mod = _load_module_isolated(
        monkeypatch,
        "isolated_script_secret_scanner_fallback",
        script_path,
        block_canonical=True,
    )

    scanner = mod.CanonicalSecretScanner()
    for token, expected_rule in [
        (_make_openai_project_key(), "OpenAI API Key"),
        (_make_openai_svcacct_key(), "OpenAI API Key"),
        (_make_anthropic_api03_key(), "Anthropic API Key"),
        (_make_aws_long_key(), "AWS Access Key ID"),
    ]:
        findings = scanner.scan_text(f'CRED_VAL = "{token}"\n')
        assert len(findings) == 1
        assert findings[0]["rule_name"] == expected_rule


# ============================================================================
# 2. SafeStorageCleaner Path Hardening Tests
# ============================================================================


def test_storage_cleaner_rejects_roots_home_workspace_and_system_dirs(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "org" / "repo"
    workspace_dir.mkdir(parents=True)
    cleaner = SafeStorageCleaner(workspace_path=workspace_dir)

    unsafe_candidates: list[Path] = [
        Path(Path.cwd().anchor),
        Path("/"),
        Path.home(),
        Path.home().parent,
        workspace_dir,
        workspace_dir / "src",
        workspace_dir.parent,
        Path("/etc"),
        Path("/etc/passwd"),
        Path("/usr"),
        Path("/usr/local"),
        Path("/var"),
        Path("/var/log"),
        Path("/bin"),
        Path("/sbin"),
        Path("/lib"),
        Path("/boot"),
        Path("/dev"),
        Path("/proc"),
        Path("/sys"),
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home() / ".ssh",
        Path.home() / ".aws",
        Path.home() / ".gnupg",
        Path.home() / ".kube",
        tmp_path / "repo" / ".git",
    ]

    if os.name == "nt":
        unsafe_candidates.extend(
            [
                Path("C:\\"),
                Path("D:\\"),
                Path("C:\\Windows"),
                Path("C:\\Windows\\System32"),
                Path("C:\\Program Files"),
                Path("C:\\Program Files (x86)"),
                Path("C:\\ProgramData"),
                Path("C:\\Users"),
            ]
        )

    for candidate in unsafe_candidates:
        assert cleaner.is_path_safe(candidate) is False, f"Expected unsafe rejected: {candidate}"


def test_storage_cleaner_rejects_empty_path(tmp_path: Path) -> None:
    cleaner = SafeStorageCleaner(workspace_path=tmp_path)
    assert cleaner.is_path_safe("") is False
    assert cleaner.is_path_safe("   ") is False
    empty_target = StorageTarget(
        category="cache",
        name="empty_path",
        path="",
        size_bytes=100,
        is_safe=True,
        description="Empty path",
    )
    res = cleaner.clean_target(empty_target, dry_run=True)
    assert res.success is False
    assert res.freed_bytes == 0


def test_storage_cleaner_preserves_safe_cache_paths(tmp_path: Path) -> None:
    cleaner = SafeStorageCleaner()

    appdata_cache = tmp_path / "AppData" / "Local" / "pip" / "cache"
    appdata_cache.mkdir(parents=True)
    safe_cache = tmp_path / "safe_cache"
    safe_cache.mkdir(parents=True)
    dot_cache = tmp_path / ".cache" / "torch"
    dot_cache.mkdir(parents=True)

    assert cleaner.is_path_safe(appdata_cache) is True
    assert cleaner.is_path_safe(safe_cache) is True
    assert cleaner.is_path_safe(dot_cache) is True
    assert cleaner.is_path_safe(Path.home()) is False
    assert cleaner.is_path_safe(Path.home() / "AppData" / "Local" / "pip" / "cache") is True
    assert cleaner.is_path_safe(Path.home() / ".cache" / "torch") is True


def test_storage_cleaner_clean_target_refuses_crafted_safe_flag_on_unsafe_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import shutil

    def _forbid_delete(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"Destructive delete invoked for unsafe path: {args} {kwargs}")

    monkeypatch.setattr(shutil, "rmtree", _forbid_delete)
    monkeypatch.setattr(Path, "unlink", _forbid_delete)

    workspace_dir = tmp_path / "org" / "repo"
    workspace_dir.mkdir(parents=True)
    cleaner = SafeStorageCleaner(workspace_path=workspace_dir)

    for label, unsafe_path in [
        ("home_dir", Path.home()),
        ("drive_anchor", Path(Path.cwd().anchor)),
        ("root_slash", Path("/")),
        ("workspace_parent", workspace_dir.parent),
    ]:
        crafted_target = StorageTarget(
            category="cache",
            name=f"crafted_{label}",
            path=str(unsafe_path),
            size_bytes=9999,
            is_safe=True,
            description="Crafted target bypassing is_safe flag",
        )
        for dry_run in (True, False):
            result = cleaner.clean_target(crafted_target, dry_run=dry_run)
            assert result.success is False, f"clean_target should refuse {unsafe_path}"
            assert result.freed_bytes == 0
            assert result.error is not None
            assert "unsafe" in result.error.lower() or "forbidden" in result.error.lower()


def test_storage_cleaner_rejects_system_temp_roots_and_preserves_subpaths(
    tmp_path: Path,
) -> None:
    cleaner = SafeStorageCleaner()
    safe_sub = tmp_path / "safe_cache"
    safe_sub.mkdir(parents=True)

    assert cleaner.is_path_safe(tempfile.gettempdir()) is False
    assert cleaner.is_path_safe("/tmp") is False
    assert cleaner.is_path_safe(safe_sub) is True


def test_storage_cleaner_rejects_onedrive_org_prefix(tmp_path: Path) -> None:
    cleaner = SafeStorageCleaner()
    corp_onedrive = tmp_path / "OneDrive - Enterprise" / "docs"
    corp_onedrive.mkdir(parents=True)

    assert cleaner.is_path_safe(corp_onedrive) is False
    assert cleaner.is_path_safe(tmp_path / "OneDrive - Acme Corp") is False


def test_storage_cleaner_rejects_symlinks_in_is_path_safe_and_clean_target(
    tmp_path: Path,
) -> None:
    cleaner = SafeStorageCleaner()
    cache_dir = tmp_path / "real_cache"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "item.bin"
    cache_file.write_bytes(b"1234")

    link_path = tmp_path / "link_to_cache"
    link_path.symlink_to(cache_dir, target_is_directory=True)

    assert cleaner.is_path_safe(link_path) is False

    target = StorageTarget(
        category="cache",
        name="symlink_cache",
        path=str(link_path),
        size_bytes=4,
        is_safe=True,
        description="Symlink pointing to cache directory",
    )
    res = cleaner.clean_target(target, dry_run=False)
    assert res.success is False
    assert res.freed_bytes == 0
    assert res.error is not None
    assert "unsafe" in res.error.lower() or "forbidden" in res.error.lower()
    assert cache_file.exists()
