"""
Corporate Autonomous Software Engineer.
Open-source enterprise agent framework for resilient and auditable software delivery.
"""

from corporate_engineer.eval.fixer import ASTSelfHealingFixer
from corporate_engineer.git_utils import (
    generate_pr_url,
    is_branch_pushed,
    push_branch_to_remote,
)
from corporate_engineer.orchestrator.adversarial import (
    AdversarialLoopCoordinator,
    AdversarialRedTeam,
    ArchitectureTranscender,
)
from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner
from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer
from corporate_engineer.rag.impact import BlastRadiusAnalyzer

__version__ = "0.1.0"

__all__ = [
    "ASTSelfHealingFixer",
    "AdversarialLoopCoordinator",
    "AdversarialRedTeam",
    "ArchitectureTranscender",
    "AutonomousEngineeringGraph",
    "BlastRadiusAnalyzer",
    "CachedASTCodebaseIndexer",
    "CanonicalSecretScanner",
    "CapabilityWiringAuditor",
    "ProactiveAnticipator",
    "QualityGateRunner",
    "SurgicalTestRunner",
    "__version__",
    "generate_pr_url",
    "is_branch_pushed",
    "push_branch_to_remote",
]
