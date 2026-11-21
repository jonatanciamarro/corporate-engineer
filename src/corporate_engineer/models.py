"""
Domain models and DTO contracts for Corporate Autonomous Engineer.
"""

from typing import Any

from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    ticket_id: str
    description: str
    workspace_path: str
    max_iterations: int = 20
    model_name: str = "gpt-4o"


class CodeDiff(BaseModel):
    file_path: str
    original_content: str | None = None
    new_content: str
    explanation: str


class TestResult(BaseModel):
    __test__ = False
    command: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    failures_detected: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
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


class MCPToolCall(BaseModel):
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    tool_name: str
    is_error: bool
    content: str


class NodeExecutionResult(BaseModel):
    node_name: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0


class Mutant(BaseModel):
    id: str
    file_path: str
    line_number: int
    original_op: str
    mutated_op: str
    status: str = "SURVIVED"  # KILLED | SURVIVED | ERROR
    killed_by_test: str | None = None


class MutationReport(BaseModel):
    total_mutants: int
    killed: int
    survived: int
    errors: int
    mutation_score: float
    mutants: list[Mutant] = Field(default_factory=list)


class EvaluationAxisScore(BaseModel):
    axis_name: str
    score: float
    weight: float
    violations: list[str] = Field(default_factory=list)
    passed: bool = True


class SemanticEvaluationReport(BaseModel):
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
                self.composite_score = round(
                    sum(a.score * a.weight for a in self.axes) / total_weight, 2
                )
            self.total_violations = sum(len(a.violations) for a in self.axes)

        if self.composite_score >= 90.0:
            self.letter_grade = "A"
        elif self.composite_score >= 80.0:
            self.letter_grade = "B"
        elif self.composite_score >= 70.0:
            self.letter_grade = "C"
        else:
            self.letter_grade = "F"

        self.passed_gate = self.composite_score >= self.min_passing_score


class ImpactNode(BaseModel):
    symbol: str
    file_path: str
    depth: int = 1
    impact_type: str = "DIRECT"  # DIRECT | TRANSITIVE
    relationship: str = "CALLS"  # CALLS | IMPORTS | INHERITS


class BlastRadiusReport(BaseModel):
    target: str
    target_type: str = "SYMBOL"  # SYMBOL | FILE
    total_impacted_files: int = 0
    total_impacted_symbols: int = 0
    impacted_nodes: list[ImpactNode] = Field(default_factory=list)
    affected_tests: list[str] = Field(default_factory=list)
    recommended_test_command: str = "pytest"


class AgentSpan(BaseModel):
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


class TraceReport(BaseModel):
    trace_id: str
    root_span_name: str = "workflow.root"
    total_spans: int = 0
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    spans: list[AgentSpan] = Field(default_factory=list)
    status: str = "OK"


class SurgicalTestReport(BaseModel):
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


class ChoiceDecision(BaseModel):
    choice: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(default_factory=dict)
    rationale: str | None = None


class NoulDecision(BaseModel):
    decision: bool
    probability: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None


class ScoreDecision(BaseModel):
    score: int | float
    level: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str | None = None


class SystemOneReport(BaseModel):
    task: str
    engine_name: str = "heuristic"
    duration_ms: float = 0.0
    choices: dict[str, ChoiceDecision] = Field(default_factory=dict)
    nouls: dict[str, NoulDecision] = Field(default_factory=dict)
    scores: dict[str, ScoreDecision] = Field(default_factory=dict)
    suggested_agent: str | None = None
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    requires_human_approval: bool = False


class TrainingSample(BaseModel):
    instruction: str = Field(min_length=1)
    input: str = ""
    output: str = Field(min_length=1)
    task_type: str = "classification"  # classification | noul | score
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetReport(BaseModel):
    total_samples: int = 0
    task_distribution: dict[str, int] = Field(default_factory=dict)
    source: str = "corporate-engineer-synthetic"
    export_path: str = ""
    hash_sha256: str = ""


class DatasetExportConfig(BaseModel):
    format: str = "jsonl"  # jsonl | alpaca | chatml
    include_metadata: bool = True
    train_test_split: float = 0.8


class FailureActionDecision(BaseModel):
    action: str  # retry | rollback | dispatch_agent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    target_agent: str | None = None
    rationale: str | None = None


class ContextPruningReport(BaseModel):
    original_symbols_count: int = 0
    pruned_symbols_count: int = 0
    original_tokens_estimate: int = 0
    pruned_tokens_estimate: int = 0
    savings_percentage: float = 0.0
    retained_symbols: list[str] = Field(default_factory=list)


class MCPServerDefinition(BaseModel):
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    transport: str = "stdio"  # stdio | sse
    url: str | None = None
    bearer_token: str | None = None
    enabled: bool = True
    max_failures: int = 3
    reset_timeout_seconds: float = 30.0


class MCPConfigFile(BaseModel):
    mcpServers: dict[str, MCPServerDefinition] = Field(default_factory=dict)


class MCPNamespacedTool(BaseModel):
    server_name: str
    tool_name: str
    namespaced_name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPHubStatus(BaseModel):
    total_servers: int = 0
    active_servers: list[str] = Field(default_factory=list)
    circuit_states: dict[str, str] = Field(default_factory=dict)
    total_tools: int = 0
    tools_by_server: dict[str, int] = Field(default_factory=dict)
