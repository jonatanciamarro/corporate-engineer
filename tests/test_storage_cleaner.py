"""
Unit and integration tests for SafeStorageCleaner.
"""

from pathlib import Path

from corporate_engineer.models import StorageTarget
from corporate_engineer.quality.storage_cleaner import SafeStorageCleaner


def test_is_path_safe_to_clean(tmp_path: Path):
    cleaner = SafeStorageCleaner()

    # Safe test cache path
    safe_cache = tmp_path / "AppData" / "Local" / "pip" / "cache"
    safe_cache.mkdir(parents=True)
    assert cleaner.is_path_safe(safe_cache) is True

    # Forbidden personal paths
    desktop_path = Path.home() / "Desktop"
    documents_path = Path.home() / "Documents"
    music_path = Path.home() / "Music"

    assert cleaner.is_path_safe(desktop_path) is False
    assert cleaner.is_path_safe(documents_path) is False
    assert cleaner.is_path_safe(music_path) is False


def test_clean_target_dry_run(tmp_path: Path):
    cleaner = SafeStorageCleaner()

    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    file1 = cache_dir / "sample.bin"
    file1.write_bytes(b"A" * 1024)  # 1 KB

    target = StorageTarget(
        category="cache",
        name="test_cache",
        path=str(cache_dir),
        size_bytes=1024,
        is_safe=True,
        description="Test cache",
    )

    result = cleaner.clean_target(target, dry_run=True)
    assert result.success is True
    assert result.freed_bytes == 1024
    assert file1.exists(), "Dry-run must not delete file"


def test_clean_target_real(tmp_path: Path):
    cleaner = SafeStorageCleaner()

    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    file1 = cache_dir / "sample.bin"
    file1.write_bytes(b"B" * 2048)  # 2 KB

    target = StorageTarget(
        category="cache",
        name="test_cache",
        path=str(cache_dir),
        size_bytes=2048,
        is_safe=True,
        description="Test cache",
    )

    result = cleaner.clean_target(target, dry_run=False)
    assert result.success is True
    assert result.freed_bytes == 2048
    assert not file1.exists(), "Real clean must remove file"


def test_clean_refuses_unsafe_path():
    cleaner = SafeStorageCleaner()

    forbidden_target = StorageTarget(
        category="personal",
        name="desktop_files",
        path=str(Path.home() / "Desktop"),
        size_bytes=1000,
        is_safe=False,
        description="Desktop files",
    )

    result = cleaner.clean_target(forbidden_target, dry_run=False)
    assert result.success is False
    assert "unsafe" in result.error.lower() or "forbidden" in result.error.lower()


def test_clean_all(tmp_path: Path):
    cleaner = SafeStorageCleaner()

    dir1 = tmp_path / "cache1"
    dir1.mkdir()
    (dir1 / "f1.dat").write_bytes(b"X" * 500)

    dir2 = tmp_path / "cache2"
    dir2.mkdir()
    (dir2 / "f2.dat").write_bytes(b"Y" * 1500)

    targets = [
        StorageTarget(
            category="cache",
            name="cache1",
            path=str(dir1),
            size_bytes=500,
            is_safe=True,
            description="c1",
        ),
        StorageTarget(
            category="cache",
            name="cache2",
            path=str(dir2),
            size_bytes=1500,
            is_safe=True,
            description="c2",
        ),
    ]

    report = cleaner.clean_all(targets=targets, dry_run=False)
    assert report.total_freed_bytes == 2000
    assert len(report.results) == 2
    assert all(r.success for r in report.results)


def test_cli_clean_dry_run(capsys):
    from corporate_engineer.cli import main

    exit_code = main(["clean", "--dry-run", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"dry_run": true' in captured.out


def test_cleaner_workspace_rejection(tmp_path: Path):
    cleaner = SafeStorageCleaner(workspace_path=tmp_path)
    # The workspace itself is forbidden
    assert cleaner.is_path_safe(tmp_path) is False
    # Subdirectories in the workspace are forbidden
    sub = tmp_path / "src"
    sub.mkdir()
    assert cleaner.is_path_safe(sub) is False


def test_clean_nonexistent_path(tmp_path: Path):
    cleaner = SafeStorageCleaner()
    target = StorageTarget(
        category="cache",
        name="nonexistent",
        path=str(tmp_path / "does_not_exist"),
        size_bytes=0,
        is_safe=True,
        description="none",
    )
    result = cleaner.clean_target(target, dry_run=False)
    assert result.success is True
    assert result.error is not None and "does not exist" in result.error.lower()


def test_calculate_size_recursive(tmp_path: Path):
    cleaner = SafeStorageCleaner()
    test_dir = tmp_path / "calc_dir"
    test_dir.mkdir()
    (test_dir / "f1.bin").write_bytes(b"1" * 100)
    nested = test_dir / "nested"
    nested.mkdir()
    (nested / "f2.bin").write_bytes(b"2" * 200)

    size = cleaner.calculate_size(test_dir)
    assert size == 300
    assert cleaner.calculate_size(tmp_path / "ghost") == 0


def test_scan_standard_targets():
    cleaner = SafeStorageCleaner()
    targets = cleaner.scan_standard_targets()
    assert isinstance(targets, list)
    for t in targets:
        assert isinstance(t, StorageTarget)
        assert t.size_bytes >= 0
