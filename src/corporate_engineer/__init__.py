"""
Corporate Autonomous Software Engineer.
Open-source enterprise agent framework for resilient and auditable software delivery.
"""

from corporate_engineer.eval.fixer import ASTSelfHealingFixer
from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer
from corporate_engineer.rag.impact import BlastRadiusAnalyzer

__version__ = "0.1.0"

__all__ = [
    "ASTSelfHealingFixer",
    "AutonomousEngineeringGraph",
    "BlastRadiusAnalyzer",
    "CachedASTCodebaseIndexer",
    "CanonicalSecretScanner",
    "ProactiveAnticipator",
    "QualityGateRunner",
    "SurgicalTestRunner",
    "__version__",
]
