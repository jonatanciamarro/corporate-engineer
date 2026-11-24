import asyncio
import threading
from unittest.mock import MagicMock, patch

from corporate_engineer.git_utils import is_branch_pushed
from corporate_engineer.mcp.client import RemoteMCPSSEClient
from corporate_engineer.mcp.hub import MCPEnterpriseHub
from corporate_engineer.models import MCPNamespacedTool, MCPServerDefinition
from corporate_engineer.orchestrator.swarm import SwarmCoordinator
from corporate_engineer.telemetry.tracer import AgentTracer


def test_git_utils_is_branch_pushed_fails_when_local_branch_invalid() -> None:
    """Verifica que is_branch_pushed retorna False se rev-parse local falhar com exit code != 0."""
    with patch("subprocess.run") as mock_run:
        # Primeiro subprocess.run: git remote
        mock_remote = MagicMock()
        mock_remote.returncode = 0
        mock_remote.stdout = "origin\n"

        # Segundo subprocess.run: git ls-remote (sucesso)
        mock_ls = MagicMock()
        mock_ls.returncode = 0
        mock_ls.stdout = "abc1234 refs/heads/feature-branch\n"

        # Terceiro subprocess.run: git rev-parse (falha: branch local inexistente/corrompida)
        mock_rev = MagicMock()
        mock_rev.returncode = 128
        mock_rev.stdout = ""
        mock_rev.stderr = "fatal: ambiguous argument 'feature-branch': unknown revision"

        mock_run.side_effect = [mock_remote, mock_ls, mock_rev]

        pushed = is_branch_pushed(branch="feature-branch")
        assert pushed is False, "Não deve retornar True quando rev-parse local falhar!"


def test_git_utils_is_branch_pushed_matches_exact_ref_not_prefix() -> None:
    """Verifica que is_branch_pushed casa a referência exata 'refs/heads/<target>' e não prefixos."""
    with patch("subprocess.run") as mock_run:
        # Primeiro subprocess.run: git remote
        mock_remote = MagicMock()
        mock_remote.returncode = 0
        mock_remote.stdout = "origin\n"

        # Segundo subprocess.run: git ls-remote com duas branches
        mock_ls = MagicMock()
        mock_ls.returncode = 0
        mock_ls.stdout = (
            "hash_extended refs/heads/feature-branch-extended\n"
            "hash_exact refs/heads/feature-branch\n"
        )

        # Terceiro subprocess.run: git rev-parse
        mock_rev = MagicMock()
        mock_rev.returncode = 0
        mock_rev.stdout = "hash_exact\n"

        mock_run.side_effect = [mock_remote, mock_ls, mock_rev]

        pushed = is_branch_pushed(branch="feature-branch")
        assert pushed is True, (
            "Deve identificar hash_exact da branch exata refs/heads/feature-branch!"
        )


def test_mcp_client_call_tool_handles_jsonrpc_root_error() -> None:
    """Verifica que RemoteMCPSSEClient.call_tool detecta erros no envelope raiz do JSON-RPC 2.0."""
    from corporate_engineer.mcp.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker()
    client = RemoteMCPSSEClient("https://mcp.internal.test/sse", circuit_breaker=breaker)
    error_response = {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": "Method not found: invalid_tool"},
        "id": 1,
    }

    with patch.object(client, "_send_request", return_value=error_response):
        res = client.call_tool("invalid_tool", {})
        assert res.is_error is True, "JSON-RPC error envelope deve resultar em is_error=True!"
        assert "Method not found" in res.content
        assert breaker.failure_count > 0, "Falha de protocolo deve registrar no CircuitBreaker!"


def test_swarm_dispatch_task_sets_success_false_on_tool_error() -> None:
    """Verifica que dispatch_task define success=False quando a ferramenta chamada retorna is_error=True."""
    hub = MCPEnterpriseHub()
    coordinator = SwarmCoordinator(hub=hub)

    # Registra servidor e tool mock que retorna erro
    server_def = MCPServerDefinition(command="test", args=[], transport="stdio")
    mock_handler = MagicMock(return_value=MagicMock(is_error=True, content="Tool internal error"))
    hub.register_server("test_srv", server_def, handler=mock_handler)

    tool = MCPNamespacedTool(
        server_name="test_srv",
        tool_name="failing_tool",
        namespaced_name="test_srv.failing_tool",
        description="Fails unconditionally",
    )
    hub.register_tool(tool)

    member = coordinator.create_swarm("goal", ["worker"])[0]
    member.allowed_tools = ["test_srv.failing_tool"]

    result = coordinator.dispatch_task(member, "run failing_tool with params")
    assert result.success is False, (
        "Tarefa deve ter success=False quando a ferramenta reportar erro!"
    )
    assert result.error is not None
    assert "Tool internal error" in result.error


def test_swarm_run_fan_out_computes_failed_tasks_accurately() -> None:
    """Verifica que run_fan_out contabiliza corretamente falhas e reprova consenso."""
    hub = MCPEnterpriseHub()
    coordinator = SwarmCoordinator(hub=hub)

    # Subtasks onde uma falha
    def mock_dispatch(m, prompt):
        from corporate_engineer.models import SwarmTaskResult

        if "fail" in prompt:
            return SwarmTaskResult(
                agent_id=m.agent_id,
                role=m.role,
                output="Failed task",
                success=False,
                error="Fatal execution failure",
                execution_time_ms=5.0,
                tools_called=[],
            )
        return SwarmTaskResult(
            agent_id=m.agent_id,
            role=m.role,
            output="Good task",
            success=True,
            error=None,
            execution_time_ms=5.0,
            tools_called=[],
        )

    subtasks = [
        {"role": "developer", "task": "task 1 ok"},
        {"role": "qa", "task": "task 2 fail"},
    ]

    with patch.object(coordinator, "dispatch_task", side_effect=mock_dispatch):
        report = coordinator.run_fan_out("Test goal", subtasks)
        assert report.failed_tasks == 1, "failed_tasks deve ser 1!"
        assert report.successful_tasks == 1, "successful_tasks deve ser 1!"
        assert "REJECTED" in report.aggregated_consensus, (
            "Consenso deve ser REJECTED quando houver tarefas falhas!"
        )


def test_swarm_coordinator_uses_reentrant_lock() -> None:
    """Verifica que SwarmCoordinator utiliza threading.RLock() ao invés de Lock comum."""
    coordinator = SwarmCoordinator()
    assert isinstance(coordinator._lock, type(threading.RLock())), (
        "SwarmCoordinator deve usar threading.RLock()!"
    )


def test_mcp_hub_uses_rlock_and_is_thread_safe() -> None:
    """Verifica que MCPEnterpriseHub possui trava RLock e tolera operações concorrentes."""
    hub = MCPEnterpriseHub()
    assert hasattr(hub, "_lock"), "MCPEnterpriseHub deve ter atributo _lock!"
    assert isinstance(hub._lock, type(threading.RLock())), (
        "MCPEnterpriseHub deve usar threading.RLock()!"
    )

    errors: list[Exception] = []

    def worker_thread(idx: int) -> None:
        try:
            for j in range(25):
                name = f"tool_{idx}_{j}"
                tool = MCPNamespacedTool(
                    server_name=f"srv_{idx}",
                    tool_name=name,
                    namespaced_name=f"srv_{idx}.{name}",
                    description="test tool",
                )
                hub.register_tool(tool)
                _ = hub.list_tools()
                _ = hub.prune_tools_for_prompt("test tool query")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Erros de concorrência no MCPEnterpriseHub: {errors}"


def test_agent_tracer_async_context_isolation() -> None:
    """Verifica que spans concorrentes em coroutines asyncio não poluem pilhas uma da outra."""
    tracer = AgentTracer("test_service")

    async def coroutine_a():
        with tracer.span("span_a") as s_a:
            await asyncio.sleep(0.02)
            return s_a.span_id

    async def coroutine_b():
        await asyncio.sleep(0.005)
        with tracer.span("span_b") as s_b:
            return s_b.parent_span_id

    async def run_both():
        return await asyncio.gather(coroutine_a(), coroutine_b())

    _, parent_of_b = asyncio.run(run_both())

    # Na arquitetura correta com ContextVar, span_b NÃO é filho de span_a
    assert parent_of_b is None, (
        "span_b não deve ter span_a como pai! Vazamento assíncrono detectado."
    )
