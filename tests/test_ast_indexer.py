from pathlib import Path

from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer


def test_ast_indexer_python_parsing(tmp_path: Path):
    sample_code = '''
"""Module docstring."""

class PaymentService:
    def process(self, amount: float) -> bool:
        return True

def standalone_helper(x: int) -> int:
    return x * 2
'''
    py_file = tmp_path / "payment.py"
    py_file.write_text(sample_code, encoding="utf-8")

    indexer = ASTCodebaseIndexer(root_path=tmp_path)
    symbols = indexer.index_file(py_file)

    assert len(symbols) >= 2
    names = [s["name"] for s in symbols]
    assert "PaymentService" in names
    assert "standalone_helper" in names


def test_ast_indexer_summary(tmp_path: Path):
    f1 = tmp_path / "service.py"
    f1.write_text("class UserAuth:\n    def login(self): pass\n", encoding="utf-8")

    indexer = ASTCodebaseIndexer(root_path=tmp_path)
    summary = indexer.build_codebase_outline()
    assert "UserAuth" in summary
    assert "login" in summary
