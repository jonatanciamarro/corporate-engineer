import pytest
from pydantic import ValidationError

from corporate_engineer.models import (
    AgentState,
    CodeDiff,
    MCPToolCall,
    MCPToolResult,
    NodeExecutionResult,
    TaskInput,
    TestResult,
)


def test_task_input_valid():
    task = TaskInput(
        ticket_id="CORP-101",
        description="Implement payment webhook handler",
        workspace_path="/workspace/project",
        max_iterations=15,
        model_name="ollama/deepseek-coder",
    )
    assert task.ticket_id == "CORP-101"
    assert task.max_iterations == 15
    assert task.model_name == "ollama/deepseek-coder"


def test_task_input_defaults():
    task = TaskInput(
        ticket_id="CORP-102",
        description="Fix race condition in token cache",
        workspace_path="/workspace",
    )
    assert task.max_iterations == 20
    assert task.model_name == "gpt-4o"


def test_task_input_missing_required():
    with pytest.raises(ValidationError):
        TaskInput(ticket_id="CORP-103")  # missing description and workspace_path


def test_code_diff_contract():
    diff = CodeDiff(
        file_path="src/service.py",
        original_content="def old(): pass",
        new_content="def new(): return True",
        explanation="Upgraded service function",
    )
    assert diff.file_path == "src/service.py"
    assert diff.original_content == "def old(): pass"
    assert diff.new_content == "def new(): return True"


def test_test_result_contract():
    res = TestResult(
        command="pytest",
        exit_code=0,
        stdout="5 passed in 0.2s",
        stderr="",
        passed=True,
    )
    assert res.passed is True
    assert res.exit_code == 0
    assert len(res.failures_detected) == 0


def test_agent_state_initialization():
    task = TaskInput(
        ticket_id="CORP-104",
        description="Setup OpenTelemetry tracing",
        workspace_path="/workspace",
    )
    state = AgentState(task=task)
    assert state.phase == "PLANNING"
    assert state.iteration_count == 0
    assert state.needs_human_approval is False
    assert len(state.code_changes) == 0
    assert len(state.test_results) == 0


def test_mcp_contracts():
    call = MCPToolCall(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )
    assert call.server_name == "filesystem"
    assert call.tool_name == "read_file"
    assert call.arguments["path"] == "README.md"

    result = MCPToolResult(
        tool_name="read_file",
        is_error=False,
        content="# Project Docs",
    )
    assert result.is_error is False
    assert result.content == "# Project Docs"


def test_node_execution_result_contract():
    res = NodeExecutionResult(
        node_name="lint_node",
        success=True,
        result={"violations": 0},
        duration_seconds=0.12,
    )
    assert res.node_name == "lint_node"
    assert res.success is True
    assert res.result == {"violations": 0}
    assert res.error is None
    assert res.duration_seconds == 0.12
