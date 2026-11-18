import keyword
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

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


def test_ast_indexer_inheritance_and_decorators(tmp_path: Path):
    code = """
@service_decorator
@audit_log
class EnterpriseBillingService(BaseService, BillingProtocol):
    \"\"\"Enterprise billing logic.\"\"\"
    @staticmethod
    def sync_calc(val: int) -> int:
        return val

    async def async_process(self, invoice_id: str) -> bool:
        return True
"""
    f = tmp_path / "billing.py"
    f.write_text(code, encoding="utf-8")

    indexer = ASTCodebaseIndexer(root_path=tmp_path)
    symbols = indexer.index_file(f)

    cls_symbol = next(s for s in symbols if s["name"] == "EnterpriseBillingService")
    assert cls_symbol["type"] == "class"
    assert "BaseService" in cls_symbol["bases"]
    assert "BillingProtocol" in cls_symbol["bases"]
    assert any("service_decorator" in d for d in cls_symbol["decorators"])
    assert any("audit_log" in d for d in cls_symbol["decorators"])
    assert "sync_calc" in cls_symbol["methods"]
    assert "async_process" in cls_symbol["async_methods"]


def test_ast_indexer_imports_and_calls(tmp_path: Path):
    code = """
import os
import sys as system
from pathlib import Path
from math import sqrt, ceil

def compute(x: float) -> float:
    validate(x)
    return ceil(sqrt(x))
"""
    f = tmp_path / "calc_imports.py"
    f.write_text(code, encoding="utf-8")

    indexer = ASTCodebaseIndexer(root_path=tmp_path)
    imports_data = indexer.extract_imports(f)

    assert "os" in imports_data["modules"]
    assert "system" in imports_data["modules"]
    assert any(
        fi["module"] == "pathlib" and "Path" in fi["names"] for fi in imports_data["from_imports"]
    )
    assert any(
        fi["module"] == "math" and "sqrt" in fi["names"] for fi in imports_data["from_imports"]
    )

    symbols = indexer.index_file(f)
    func_sym = next(s for s in symbols if s["name"] == "compute")
    assert "validate" in func_sym["calls"]
    assert "ceil" in func_sym["calls"]
    assert "sqrt" in func_sym["calls"]


def test_ast_indexer_hierarchy_map(tmp_path: Path):
    (tmp_path / "base.py").write_text("class BaseWorker:\n    pass\n", encoding="utf-8")
    (tmp_path / "w1.py").write_text(
        "class ComputeWorker(BaseWorker):\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "w2.py").write_text(
        "class NetworkWorker(BaseWorker):\n    pass\n", encoding="utf-8"
    )

    indexer = ASTCodebaseIndexer(root_path=tmp_path)
    hierarchy = indexer.build_hierarchy_map()

    assert "BaseWorker" in hierarchy
    subclasses = hierarchy["BaseWorker"]
    assert "ComputeWorker" in subclasses
    assert "NetworkWorker" in subclasses


# Property-Based Testing with Hypothesis
valid_identifier = st.from_regex(r"^[a-zA-Z_][a-zA-Z0-9_]{0,20}$", fullmatch=True)


@given(
    cls_name=valid_identifier,
    base_name=valid_identifier,
    method_name=valid_identifier,
    docstring=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),  # type: ignore[arg-type]
            blacklist_characters="\x00",
        ),
        max_size=50,
    ),
)
@settings(max_examples=30, deadline=None)
def test_pbt_ast_indexer_properties(tmp_path_factory, cls_name, base_name, method_name, docstring):
    if (
        cls_name == base_name
        or method_name == cls_name
        or keyword.iskeyword(cls_name)
        or keyword.iskeyword(base_name)
        or keyword.iskeyword(method_name)
    ):
        return

    tmp_dir = tmp_path_factory.mktemp("pbt_ast")
    code = f"""
class {cls_name}({base_name}):
    {docstring!r}
    def {method_name}(self):
        pass
"""
    f = tmp_dir / "generated.py"
    f.write_text(code, encoding="utf-8")

    indexer = ASTCodebaseIndexer(root_path=tmp_dir)
    symbols = indexer.index_file(f)

    assert len(symbols) == 1
    sym = symbols[0]
    assert sym["name"] == cls_name
    assert base_name in sym["bases"]
    assert method_name in sym["methods"]
