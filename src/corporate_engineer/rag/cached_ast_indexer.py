"""
Cached AST Codebase Indexer using SHA-256 content hashing.
Implements the content-hash-cache-pattern to avoid redundant AST parsing of unchanged files.
"""
import hashlib
import json
from pathlib import Path
from typing import Any
from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer

class CachedASTCodebaseIndexer(ASTCodebaseIndexer):
    """
    Extends ASTCodebaseIndexer with persistent, content-hash-based disk caching.
    Stores extracted symbols and metadata indexed by file SHA-256 digest in .cache/ast_index_cache.json.
    """

    def __init__(self, root_path: Path, cache_path: Path | None=None) -> None:
        super().__init__(root_path=root_path)
        self.cache_path = cache_path or self.root_path / '.cache' / 'ast_index_cache.json'
        self._cache: dict[str, dict[str, Any]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    self._cache = data
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        hasher = hashlib.sha256()
        try:
            hasher.update(file_path.read_bytes())
            return hasher.hexdigest()
        except OSError:
            return ''

    def _get_cache_key(self, file_path: Path) -> str:
        try:
            return str(file_path.resolve().relative_to(self.root_path))
        except ValueError:
            return str(file_path.name)

    def index_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Index a Python file, retrieving from cache if content SHA-256 matches."""
        key = self._get_cache_key(file_path)
        current_hash = self.compute_file_hash(file_path)
        if not current_hash:
            return super().index_file(file_path)
        cached_entry = self._cache.get(key)
        if cached_entry and cached_entry.get('sha256') == current_hash and ('symbols' in cached_entry):
            self._hits += 1
            return list(cached_entry['symbols'])
        self._misses += 1
        symbols = super().index_file(file_path)
        if key not in self._cache:
            self._cache[key] = {}
        self._cache[key]['sha256'] = current_hash
        self._cache[key]['symbols'] = symbols
        self.save_cache()
        return symbols

    def extract_imports(self, file_path: Path) -> dict[str, Any]:
        """Extract imports from file, using cache if content SHA-256 matches."""
        key = self._get_cache_key(file_path)
        current_hash = self.compute_file_hash(file_path)
        if not current_hash:
            return super().extract_imports(file_path)
        cached_entry = self._cache.get(key)
        if cached_entry and cached_entry.get('sha256') == current_hash and ('imports' in cached_entry):
            self._hits += 1
            return dict(cached_entry['imports'])
        imports_data = super().extract_imports(file_path)
        if key not in self._cache:
            self._cache[key] = {}
        self._cache[key]['sha256'] = current_hash
        self._cache[key]['imports'] = imports_data
        self.save_cache()
        return imports_data

    def save_cache(self) -> None:
        """Persist current cache index to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding='utf-8')
        except OSError:
            pass

    def clear_cache(self) -> None:
        """Clear cache both in-memory and on disk."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
            except OSError:
                pass

    def get_cache_stats(self) -> dict[str, int]:
        """Return cache performance statistics."""
        return {'cached_files': len(self._cache), 'hits': self._hits, 'misses': self._misses}
