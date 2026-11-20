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
