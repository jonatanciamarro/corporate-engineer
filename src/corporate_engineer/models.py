"""
Domain models and DTO contracts for Corporate Autonomous Engineer.
"""

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone

    UTC = timezone.utc  # noqa: UP017 # type: ignore[assignment]
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _FrozenDTO(BaseModel):
    """Base contract/report/state DTO enforcing strict Pydantic v2 immutability (IMP-0040)."""

    model_config = ConfigDict(frozen=True)


class TaskInput(_FrozenDTO):
    ticket_id: str
    description: str
    workspace_path: str
    max_iterations: int = 20
    model_name: str = "gpt-4o"


class CodeDiff(_FrozenDTO):
    file_path: str
    original_content: str | None = None
    new_content: str
    explanation: str


class TestResult(_FrozenDTO):
    __test__ = False
    command: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    failures_detected: list[str] = Field(default_factory=list)


class AgentState(_FrozenDTO):
    task: TaskInput
    plan: str | None = None
    contracts: dict[str, Any] = Field(default_factory=dict)
    test_files: list[str] = Field(default_factory=list)
    code_changes: list[CodeDiff] = Field(default_factory=list)
    test_results: list[TestResult] = Field(default_factory=list)
    iteration_count: int = 0
    phase: str = "PLANNING"  # PLANNING -> TDD -> IMPLEMENT -> AUDIT -> DELIVER
    needs_human_approval: bool = False
    error: str | None = None


class MCPToolCall(_FrozenDTO):
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(_FrozenDTO):
    tool_name: str
    is_error: bool
    content: str


class NodeExecutionResult(_FrozenDTO):
    node_name: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0


class Mutant(_FrozenDTO):
    id: str
    file_path: str
    line_number: int
    original_op: str
    mutated_op: str
    status: str = "SURVIVED"  # KILLED | SURVIVED | ERROR
    killed_by_test: str | None = None
    error_message: str | None = None


class MutationReport(_FrozenDTO):
    total_mutants: int
    killed: int
    survived: int
    errors: int
    mutation_score: float
    mutants: list[Mutant] = Field(default_factory=list)


class EvaluationAxisScore(_FrozenDTO):
    axis_name: str
    score: float
    weight: float
    violations: list[str] = Field(default_factory=list)
    passed: bool = True


class SemanticEvaluationReport(_FrozenDTO):
    target_path: str
    axes: list[EvaluationAxisScore] = Field(default_factory=list)
    total_files_evaluated: int = 0
    total_functions_evaluated: int = 0
    min_passing_score: float = 80.0
    composite_score: float = 0.0
    letter_grade: str = "A"
    passed_gate: bool = True
    total_violations: int = 0

    def model_post_init(self, context: Any, /) -> None:
        if self.axes:
            total_weight = sum(a.weight for a in self.axes)
            if total_weight > 0:
                object.__setattr__(
                    self,
                    "composite_score",
                    round(sum(a.score * a.weight for a in self.axes) / total_weight, 2),
                )
            object.__setattr__(self, "total_violations", sum(len(a.violations) for a in self.axes))

        if self.composite_score >= 90.0:
            letter = "A"
        elif self.composite_score >= 80.0:
            letter = "B"
        elif self.composite_score >= 70.0:
            letter = "C"
        else:
            letter = "F"

        object.__setattr__(self, "letter_grade", letter)
        object.__setattr__(self, "passed_gate", self.composite_score >= self.min_passing_score)


class ImpactNode(_FrozenDTO):
    symbol: str
    file_path: str
    depth: int = 1
    impact_type: str = "DIRECT"  # DIRECT | TRANSITIVE
    relationship: str = "CALLS"  # CALLS | IMPORTS | INHERITS


class BlastRadiusReport(_FrozenDTO):
    target: str
    target_type: str = "SYMBOL"  # SYMBOL | FILE
    total_impacted_files: int = 0
    total_impacted_symbols: int = 0
    impacted_nodes: list[ImpactNode] = Field(default_factory=list)
    affected_tests: list[str] = Field(default_factory=list)
    recommended_test_command: str = "pytest"


class AgentSpan(BaseModel):
    """Mutable runtime telemetry span handle populated between start_span() and end_span()."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time_iso: str
    end_time_iso: str | None = None
    duration_ms: float = 0.0
    status: str = "OK"  # OK | ERROR | UNSET
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None


class TraceReport(_FrozenDTO):
    trace_id: str
    root_span_name: str = "workflow.root"
    total_spans: int = 0
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    spans: list[AgentSpan] = Field(default_factory=list)
    status: str = "OK"


class SurgicalTestReport(_FrozenDTO):
    base_branch: str = "main"
    changed_files: list[str] = Field(default_factory=list)
    affected_tests: list[str] = Field(default_factory=list)
    command: str = ""
    executed: bool = False
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    passed: bool = True


class ChoiceDecision(_FrozenDTO):
    choice: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(default_factory=dict)
    rationale: str | None = None


class NoulDecision(_FrozenDTO):
    decision: bool
    probability: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None


class ScoreDecision(_FrozenDTO):
    score: int | float
    level: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str | None = None


class SystemOneReport(_FrozenDTO):
    task: str
    engine_name: str = "heuristic"
    fallback_reason: str | None = None
    duration_ms: float = 0.0
    choices: dict[str, ChoiceDecision] = Field(default_factory=dict)
    nouls: dict[str, NoulDecision] = Field(default_factory=dict)
    scores: dict[str, ScoreDecision] = Field(default_factory=dict)
    suggested_agent: str | None = None
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    requires_human_approval: bool = False


class TrainingSample(_FrozenDTO):
    instruction: str = Field(min_length=1)
    input: str = ""
    output: str = Field(min_length=1)
    task_type: str = "classification"  # classification | noul | score
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetReport(_FrozenDTO):
    total_samples: int = 0
    task_distribution: dict[str, int] = Field(default_factory=dict)
    source: str = "corporate-engineer-synthetic"
    export_path: str = ""
    hash_sha256: str = ""


class DatasetExportConfig(_FrozenDTO):
    format: str = "jsonl"  # jsonl | alpaca | chatml
    include_metadata: bool = True
    train_test_split: float = 0.8


class FailureActionDecision(_FrozenDTO):
    action: str  # retry | rollback | dispatch_agent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    target_agent: str | None = None
    rationale: str | None = None


class ContextPruningReport(_FrozenDTO):
    original_symbols_count: int = 0
    pruned_symbols_count: int = 0
    original_tokens_estimate: int = 0
    pruned_tokens_estimate: int = 0
    savings_percentage: float = 0.0
    retained_symbols: list[str] = Field(default_factory=list)


class MCPServerDefinition(_FrozenDTO):
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    transport: str = "stdio"  # stdio | sse
    url: str | None = None
    bearer_token: str | None = None
    enabled: bool = True
    max_failures: int = 3
    reset_timeout_seconds: float = 30.0


class MCPConfigFile(_FrozenDTO):
    mcpServers: dict[str, MCPServerDefinition] = Field(default_factory=dict)


class MCPNamespacedTool(_FrozenDTO):
    server_name: str
    tool_name: str
    namespaced_name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPHubStatus(_FrozenDTO):
    total_servers: int = 0
    active_servers: list[str] = Field(default_factory=list)
    circuit_states: dict[str, str] = Field(default_factory=dict)
    total_tools: int = 0
    tools_by_server: dict[str, int] = Field(default_factory=dict)


class FixDetail(_FrozenDTO):
    file_path: str
    rule_name: str
    line_number: int = 1
    description: str
    original_snippet: str = ""
    fixed_snippet: str = ""


class FixReport(_FrozenDTO):
    total_files_analyzed: int = 0
    files_modified: int = 0
    fixes_applied: list[FixDetail] = Field(default_factory=list)
    dry_run: bool = False
    system_one_risk: str = "LOW"
    success: bool = True


class StorageTarget(_FrozenDTO):
    category: str  # "cache", "model", "audio_cache", "temp"
    name: str  # "gpt4all_model", "ollama_model", "spotify_cache", "pip_cache"
    path: str
    size_bytes: int = 0
    is_safe: bool = True
    description: str = ""


class StorageCleanResult(_FrozenDTO):
    target_name: str
    path: str
    freed_bytes: int = 0
    success: bool
    error: str | None = None


class StorageOptimizationReport(_FrozenDTO):
    total_freed_bytes: int = 0
    total_freed_gb: float = 0.0
    results: list[StorageCleanResult] = Field(default_factory=list)
    dry_run: bool = False


class EngineLatencyStats(_FrozenDTO):
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


class EngineBenchmarkResult(_FrozenDTO):
    engine_name: str
    total_samples: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    accuracy_percent: float = 0.0
    latency: EngineLatencyStats = Field(default_factory=EngineLatencyStats)
    throughput_rps: float = 0.0
    memory_rss_mb: float | None = None
    per_mode_accuracy: dict[str, float] = Field(default_factory=dict)
    error_summary: list[str] = Field(default_factory=list)


class BenchmarkReport(_FrozenDTO):
    timestamp: str
    dataset_path: str
    sample_count: int = 0
    iterations: int = 1
    engines: dict[str, EngineBenchmarkResult] = Field(default_factory=dict)
    winner_latency: str = ""
    winner_accuracy: str = ""
    recommendations: list[str] = Field(default_factory=list)


class SwarmMember(BaseModel):
    """Mutable runtime worker handle updated under RLock during SwarmCoordinator dispatch."""

    agent_id: str
    role: str
    task_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    status: str = "IDLE"  # IDLE, WORKING, COMPLETED, FAILED


class SwarmTaskResult(_FrozenDTO):
    agent_id: str
    role: str
    output: str
    success: bool
    status: str = "COMPLETED"
    execution_time_ms: float = 0.0
    tools_called: list[str] = Field(default_factory=list)
    error: str | None = None


class SwarmGoalReport(_FrozenDTO):
    goal: str
    swarm_name: str
    total_agents: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    execution_mode: str = "deterministic-analyzer"
    aggregated_consensus: str = ""
    results: list[SwarmTaskResult] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    recommendations: list[str] = Field(default_factory=list)


class RevisedPromptSpec(_FrozenDTO):
    raw_prompt: str
    target_domain: str = "general"
    core_intent: str = ""
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    tdd_test_scenarios: list[str] = Field(default_factory=list)
    metaprompt: str = ""
    confidence_score: float = 0.0
    is_bypassed: bool = False
    bypass_reason: str | None = None
    timestamp: str = ""


class RunExecutionReport(_FrozenDTO):
    ticket_id: str
    task_description: str
    status: str = "SUCCESS"  # SUCCESS | SIMULATED_NO_EXECUTOR | FAILED | AUDIT_FAILED | BUDGET_EXCEEDED | PENDING_APPROVAL
    final_phase: str = "DELIVER"
    iterations: int = 0
    checkpoints_created: list[str] = Field(default_factory=list)
    refined_plan: str | None = None
    test_files: list[str] = Field(default_factory=list)
    code_changes_count: int = 0
    audit_passed: bool = True
    is_simulated: bool = False
    warnings: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    trace_id: str | None = None
    dry_run: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class LoraDomain(str, Enum):
    MOTION_REMOTION = "MOTION_REMOTION"
    MOTION_MANIM = "MOTION_MANIM"
    MOTION_BLENDER = "MOTION_BLENDER"
    TOOL_CALLING = "TOOL_CALLING"


class LoraTrainingSample(_FrozenDTO):
    id: str
    domain: LoraDomain
    system_instruction: str = ""
    user_prompt: str
    target_response: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_valid: bool = True
    syntax_errors: list[str] = Field(default_factory=list)


class LoraDatasetConfig(_FrozenDTO):
    domains: list[LoraDomain] = Field(
        default_factory=lambda: [
            LoraDomain.MOTION_REMOTION,
            LoraDomain.MOTION_MANIM,
            LoraDomain.MOTION_BLENDER,
            LoraDomain.TOOL_CALLING,
        ]
    )
    samples_per_domain: int = 10
    train_split_ratio: float = Field(default=0.8, gt=0.0, lt=1.0)
    seed: int = 42
    sanitize_secrets: bool = True
    darkfactory_aesthetic: bool = True


class LoraValidationReport(_FrozenDTO):
    total_samples: int
    valid_samples: int
    invalid_samples: int
    domain_breakdown: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    is_approved: bool = True


class LoraExportResult(_FrozenDTO):
    train_file: str
    validation_file: str
    train_count: int
    validation_count: int
    estimated_tokens: int
    success: bool = True
    sanitized_secrets_count: int = 0


class AnticipationStep(_FrozenDTO):
    step_index: int = Field(
        ge=1, description="Index of the anticipation step (1 for immediate, 2 for subsequent)"
    )
    phase: str = Field(
        description="Pipeline phase, e.g. PLANNING, CONTRACT/TDD, IMPLEMENT, AUDIT, DELIVER"
    )
    action: str = Field(description="Concise description of the recommended action")
    rationale: str = Field(
        default="", description="Why this step is critical before moving forward"
    )
    target_files: list[str] = Field(
        default_factory=list, description="Files expected to be created or modified"
    )
    tdd_scenario: str = Field(default="", description="Shift-Left TDD scenario to prove behavior")


class AnticipationPlan(_FrozenDTO):
    raw_prompt: str
    target_domain: str = Field(
        default="orchestrator", description="Target domain detected by context refiner"
    )
    risk_level: str = Field(default="LOW", description="Risk level (LOW, MEDIUM, HIGH)")
    recommended_agents: list[str] = Field(
        default_factory=list, description="Subagents mapped to execute the task"
    )
    step_immediate_1: AnticipationStep = Field(
        description="Step 1: Immediate action (e.g. contracts, ADR, TDD red test)"
    )
    step_subsequent_2: AnticipationStep = Field(
        description="Step 2: Subsequent action (e.g. implementation, blast radius, audit)"
    )
    blast_radius_estimate: list[str] = Field(
        default_factory=list, description="Files likely affected downstream"
    )
    structured_metaprompt: str = Field(
        default="", description="Refined metaprompt guidance for LLM execution"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ==============================================================================
# IMP-0026: Tri-Phase Adversarial Loop DTO Models (ADR-028)
# ==============================================================================


class RedTeamVulnerabilitySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RedTeamThreatCategory(str, Enum):
    CONCURRENCY = "CONCURRENCY"
    FAULT_TOLERANCE = "FAULT_TOLERANCE"
    PRIVILEGE_MCP = "PRIVILEGE_MCP"
    NETWORK_TIMEOUTS = "NETWORK_TIMEOUTS"
    DATA_INTEGRITY = "DATA_INTEGRITY"


class RedTeamVulnerability(_FrozenDTO):
    id: str = Field(description="Unique vulnerability identifier, e.g. VULN-001")
    category: RedTeamThreatCategory = Field(description="Threat classification category")
    severity: RedTeamVulnerabilitySeverity = Field(description="Vulnerability severity level")
    title: str = Field(description="Concise description of the flaw")
    description: str = Field(description="Detailed architectural or behavioral vulnerability")
    attack_vector: str = Field(description="How an adversary or pathological state exploits this")
    target_component: str = Field(default="", description="Affected module, class, or function")


class RedTeamAttackReport(_FrozenDTO):
    plan_id: str = Field(description="Identifier of the target plan or ticket")
    total_vulnerabilities: int = Field(default=0, description="Total detected flaws")
    vulnerabilities: list[RedTeamVulnerability] = Field(
        default_factory=list, description="Enumerated flaws"
    )
    highest_severity: RedTeamVulnerabilitySeverity = Field(
        default=RedTeamVulnerabilitySeverity.LOW, description="Highest severity observed"
    )
    attack_narrative: str = Field(default="", description="Consolidated red team assessment")
    is_blocked: bool = Field(
        default=False, description="True if CRITICAL or HIGH severity flaws block execution"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TranscendenceHardening(_FrozenDTO):
    vulnerability_id: str = Field(description="Reference to targeted RedTeamVulnerability id")
    original_weakness: str = Field(description="Summary of the original vulnerability")
    transcendence_strategy: str = Field(
        description="Architectural synthesis resolving the weakness"
    )
    formal_invariant: str = Field(description="Formal invariant guaranteeing system immunity")
    resilience_mechanism: str = Field(
        description="Concrete implementation pattern (e.g. RLock, CircuitBreaker, Sandbox)"
    )


class TranscendencePlan(_FrozenDTO):
    plan_id: str = Field(description="Plan or ticket identifier")
    hardenings: list[TranscendenceHardening] = Field(
        default_factory=list, description="Hardening mappings"
    )
    transcended_architecture: str = Field(
        default="", description="Synthesized hardened architecture description"
    )
    structural_invariants: list[str] = Field(
        default_factory=list, description="Formal invariants enforced"
    )
    residual_risk: str = Field(default="LOW", description="Estimated residual risk level")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChaosTestCase(_FrozenDTO):
    case_id: str = Field(description="Identifier for chaos scenario, e.g. CHAOS-001")
    vulnerability_id: str = Field(default="", description="Related vulnerability identifier")
    name: str = Field(description="Descriptive name of chaos test")
    category: str = Field(default="CHAOS", description="Category of chaos experiment")
    injection_trigger: str = Field(description="Condition or fault injected")
    expected_behavior: str = Field(
        description="Required resilient response (e.g. raises typed error, falls back, retries)"
    )
    tdd_scenario: str = Field(description="Exact pytest function test specification")


class RedTeamVerdictStatus(str, Enum):
    VERIFIED = "VERIFIED"
    HARDEN_REQUIRED = "HARDEN_REQUIRED"
    REJECTED = "REJECTED"
    BYPASSED = "BYPASSED"


class AdversarialVerdict(_FrozenDTO):
    status: RedTeamVerdictStatus = Field(description="Final adversarial status")
    iterations_completed: int = Field(default=1, description="Number of dialectical rounds")
    unresolved_vulnerabilities: list[str] = Field(
        default_factory=list, description="IDs of unresolved flaws"
    )
    chaos_matrix: list[ChaosTestCase] = Field(
        default_factory=list, description="Mandatory chaos test suite for TDD"
    )
    confidence_score: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0")
    bypassed: bool = Field(default=False, description="Whether the loop was bypassed via fast-path")
    bypass_reason: str = Field(default="", description="Reason for bypass")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class DialecticalLoopResult(_FrozenDTO):
    plan_id: str = Field(description="Plan identifier")
    initial_attack: RedTeamAttackReport = Field(description="Phase 1.5 attack report")
    transcendence: TranscendencePlan | None = Field(
        default=None, description="Phase 1.6 transcendence plan"
    )
    re_verification: RedTeamAttackReport | None = Field(
        default=None, description="Phase 1.7 re-verification report"
    )
    verdict: AdversarialVerdict = Field(description="Consolidated adversarial verdict")
    duration_ms: float = Field(default=0.0, description="Duration of dialectical loop in ms")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ==============================================================================
# IMP-0029: Continuous Capability Auto-Wiring DTO Models (ADR-028)
# ==============================================================================


class ModuleWiringStatus(_FrozenDTO):
    module_path: str = Field(description="Relative path of the module")
    is_exported: bool = Field(default=False, description="Whether primary symbols are exported")
    has_test_coverage: bool = Field(default=False, description="Whether matching test exists")
    is_cli_registered: bool = Field(default=False, description="Whether exposed in CLI")
    is_domain_mapped: bool = Field(default=False, description="Whether mapped in prompt refiner")
    exported_symbols: list[str] = Field(default_factory=list, description="Public exported symbols")


class WiringAuditReport(_FrozenDTO):
    total_modules: int = Field(default=0, description="Total source modules audited")
    connected_modules: list[str] = Field(default_factory=list, description="Fully wired modules")
    unwired_modules: list[str] = Field(
        default_factory=list, description="Unwired or orphan modules"
    )
    missing_test_modules: list[str] = Field(
        default_factory=list, description="Modules without tests"
    )
    orphan_symbols: list[str] = Field(
        default_factory=list, description="Unused/orphan public symbols"
    )
    passed: bool = Field(default=True, description="Whether wiring audit cleared quality gate")
    remediation_actions: list[str] = Field(
        default_factory=list, description="Actionable remediation steps"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ==============================================================================
# IMP-0042: Native Stdio MCP Server DTO Models (ADR-036)
# ==============================================================================


class MCPServerToolSpec(_FrozenDTO):
    """Specification for a single tool exposed by CorporateEngineerMCPServer."""

    name: str = Field(description="MCP tool identifier")
    description: str = Field(description="Human/agent-readable tool purpose")
    mutating: bool = Field(default=False, description="Whether the tool can modify workspace files")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema defining expected tool arguments"
    )


class MCPServerCapabilitiesReport(_FrozenDTO):
    """Runtime capability report for CorporateEngineerMCPServer."""

    server_name: str = Field(default="corporate-engineer-mcp", description="MCP server identifier")
    protocol_version: str = Field(
        default="2024-11-05", description="Supported MCP JSON-RPC protocol version"
    )
    workspace_root: str = Field(description="Confined absolute workspace root")
    allow_mutations: bool = Field(default=False, description="Whether mutating tools are enabled")
    registered_tools: list[str] = Field(
        default_factory=list, description="Tool names exposed under current policy"
    )
