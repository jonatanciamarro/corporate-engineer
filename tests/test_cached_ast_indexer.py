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
