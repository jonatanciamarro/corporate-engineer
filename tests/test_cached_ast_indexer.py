import json
from pathlib import Path

from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer


def test_cached_ast_indexer_first_run_and_subsequent_cache_hit(tmp_path: Path):
    cache_file = tmp_path / ".cache" / "ast_index_cache.json"
    code_file = tmp_path / "calc.py"
    code_file.write_text(
        "class Calculator:\n    def add(self, a: int, b: int) -> int:\n        return a + b\n",
        encoding="utf-8",
    )

    indexer = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)

    # First indexing run (Cache Miss)
    symbols_1 = indexer.index_file(code_file)
    stats_1 = indexer.get_cache_stats()
    assert stats_1["misses"] == 1
    assert stats_1["hits"] == 0
    assert cache_file.exists()

    # Verify cache content structure
    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
    assert "calc.py" in cache_data
    assert "sha256" in cache_data["calc.py"]
    assert "symbols" in cache_data["calc.py"]

    # Second indexing run (Cache Hit)
    indexer_2 = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    symbols_2 = indexer_2.index_file(code_file)
    stats_2 = indexer_2.get_cache_stats()
    assert stats_2["hits"] == 1
    assert stats_2["misses"] == 0
    assert symbols_1 == symbols_2


def test_cached_ast_indexer_imports_caching(tmp_path: Path):
    cache_file = tmp_path / ".cache" / "ast_index_cache.json"
    code_file = tmp_path / "importer.py"
    code_file.write_text("import sys\nfrom math import sqrt\n", encoding="utf-8")

    indexer = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)

    # First extraction
    imports_1 = indexer.extract_imports(code_file)
    assert "sys" in imports_1["modules"]
    assert any(fi["module"] == "math" and "sqrt" in fi["names"] for fi in imports_1["from_imports"])

    # Second extraction from cache
    imports_2 = indexer.extract_imports(code_file)
    assert imports_1 == imports_2
    assert indexer.get_cache_stats()["hits"] >= 1


def test_cached_ast_indexer_invalidation_on_content_change(tmp_path: Path):
    cache_file = tmp_path / ".cache" / "ast_index_cache.json"
    code_file = tmp_path / "module.py"
    code_file.write_text("def hello(): pass\n", encoding="utf-8")

    indexer = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    symbols_1 = indexer.index_file(code_file)
    assert any(s["name"] == "hello" for s in symbols_1)

    # Modify file content
    code_file.write_text("def goodbye(): pass\n", encoding="utf-8")
    symbols_2 = indexer.index_file(code_file)
    assert any(s["name"] == "goodbye" for s in symbols_2)
    assert not any(s["name"] == "hello" for s in symbols_2)


def test_cached_ast_indexer_clear_cache(tmp_path: Path):
    cache_file = tmp_path / ".cache" / "ast_index_cache.json"
    code_file = tmp_path / "test.py"
    code_file.write_text("x = 1\n", encoding="utf-8")

    indexer = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    indexer.index_file(code_file)
    assert cache_file.exists()

    indexer.clear_cache()
    assert not cache_file.exists()
    assert indexer.get_cache_stats()["cached_files"] == 0


def test_get_all_symbol_names_walks_new_modified_and_deleted_files(tmp_path: Path) -> None:
    """IMP-0033: Partial cache must not starve discovery of new, modified, or deleted files."""
    cache_file = tmp_path / ".cache" / "ast_index_cache.json"
    file_a = tmp_path / "alpha.py"
    file_a.write_text("class AlphaService:\n    pass\n", encoding="utf-8")

    # Populate partial cache with only alpha.py
    indexer_1 = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    indexer_1.index_file(file_a)
    assert indexer_1.get_all_symbol_names() == {"AlphaService"}

    # Add beta.py and an excluded directory file that must be ignored
    file_b = tmp_path / "beta.py"
    file_b.write_text("def beta_runner() -> None:\n    pass\n", encoding="utf-8")
    ignored_dir = tmp_path / ".venv"
    ignored_dir.mkdir()
    (ignored_dir / "ignored.py").write_text("class ShouldBeIgnored:\n    pass\n", encoding="utf-8")

    # Fresh indexer loads partial cache (containing alpha.py) and calls get_all_symbol_names()
    indexer_2 = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    names_after_add = indexer_2.get_all_symbol_names()
    assert names_after_add == {"AlphaService", "beta_runner"}
    stats = indexer_2.get_cache_stats()
    assert stats["hits"] >= 1  # alpha.py served from O(1) SHA-256 cache
    assert stats["misses"] >= 1  # beta.py newly indexed

    # Modify beta.py and delete alpha.py -> stale cache entry pruned, updated symbols returned
    file_b.write_text("def beta_v2() -> None:\n    pass\n", encoding="utf-8")
    file_a.unlink()

    indexer_3 = CachedASTCodebaseIndexer(root_path=tmp_path, cache_path=cache_file)
    names_after_update = indexer_3.get_all_symbol_names()
    assert names_after_update == {"beta_v2"}
    assert indexer_3.get_cache_stats()["cached_files"] == 1
