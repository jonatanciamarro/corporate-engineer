"""
Tests for OpenTelemetry Agent Tracing & Span Telemetry (IMP-0009).
Validates span generation, parent-child hierarchies, error capture, DAG integration,
and CLI telemetry commands.
"""

from pathlib import Path

import pytest

from corporate_engineer.cli import main
from corporate_engineer.models import AgentSpan, TaskInput, TraceReport
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.telemetry.tracer import AgentTracer


def test_models_agent_span_and_trace_report() -> None:
    span = AgentSpan(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        name="dag.node.architect",
        start_time_iso="2026-11-20T02:00:00Z",
        end_time_iso="2026-11-20T02:00:01Z",
        duration_ms=1000.0,
        status="OK",
        attributes={"gen_ai.system": "gemini", "gen_ai.usage.prompt_tokens": 120},
    )

    report = TraceReport(
        trace_id=span.trace_id,
        root_span_name="dag.workflow",
        total_spans=1,
        total_duration_ms=1000.0,
        total_tokens=120,
        spans=[span],
        status="OK",
    )

    assert report.total_spans == 1
    assert report.total_tokens == 120
    assert report.spans[0].name == "dag.node.architect"


def test_agent_tracer_hierarchy_and_context_manager() -> None:
    tracer = AgentTracer()

    with (
        tracer.span("workflow.root", attributes={"service": "corporate-engineer"}),
        tracer.span("subagent.planner", attributes={"agent": "planner"}) as child_span,
    ):
        child_span.attributes["tokens"] = 50

    report = tracer.export_trace()

    assert report.total_spans == 2
    assert report.total_tokens == 50
    assert report.status == "OK"

    # Hierarchy verification
    root_s = next(s for s in report.spans if s.name == "workflow.root")
    child_s = next(s for s in report.spans if s.name == "subagent.planner")

    assert root_s.parent_span_id is None
    assert child_s.parent_span_id == root_s.span_id
    assert child_s.duration_ms >= 0.0


def test_agent_tracer_error_capture() -> None:
    tracer = AgentTracer()

    with (
        pytest.raises(ValueError, match="Simulated agent failure"),
        tracer.span("failing.node") as span,
    ):
        span.attributes["step"] = "init"
        raise ValueError("Simulated agent failure")

    report = tracer.export_trace()
    assert report.total_spans == 1
    failed_span = report.spans[0]
    assert failed_span.status == "ERROR"
    assert "Simulated agent failure" in (failed_span.error_message or "")


def test_agent_tracer_export_json(tmp_path: Path) -> None:
    tracer = AgentTracer()
    with tracer.span("test.operation", attributes={"env": "test"}):
        pass

    out_file = tmp_path / "trace.json"
    json_str = tracer.export_json(output_path=out_file)

    assert out_file.exists()
    assert "test.operation" in json_str
    assert "trace_id" in json_str


def test_dag_orchestrator_telemetry_integration(tmp_path: Path) -> None:
    task = TaskInput(
        ticket_id="IMP-TEST",
        description="Test DAG tracing",
        workspace_path=str(tmp_path),
        max_iterations=1,
    )
    graph = AutonomousEngineeringGraph(task=task)
    # Check that tracer is present
    assert hasattr(graph, "tracer")
    assert isinstance(graph.tracer, AgentTracer)

    # Execute step and verify spans created
    graph.execute_step()
    report = graph.get_trace_report()
    assert report.total_spans >= 1
    assert any("dag.node." in s.name for s in report.spans)


def test_cli_telemetry_and_dag_trace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Test dag --trace
    code_dag = main(["dag", "--trace", "--workspace", str(tmp_path)])
    assert code_dag == 0
    captured_dag = capsys.readouterr()
    assert "Trace" in captured_dag.out or "telemetry" in captured_dag.out.lower()

    # Save a dummy trace and test telemetry CLI
    tracer = AgentTracer()
    with tracer.span("cli.test", attributes={"cost": 0.01}):
        pass
    trace_path = tmp_path / "sample_trace.json"
    tracer.export_json(output_path=trace_path)

    code_tel = main(["telemetry", "--file", str(trace_path), "--format", "json"])
    assert code_tel == 0
    captured_tel = capsys.readouterr()
    assert "cli.test" in captured_tel.out
