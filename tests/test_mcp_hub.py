"""
Tests for MCP Enterprise Hub & Tool Multiplexer (.mcp.json pools) (IMP-0011).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corporate_engineer.mcp.circuit_breaker import CircuitState
from corporate_engineer.mcp.hub import MCPEnterpriseHub
from corporate_engineer.models import (
    MCPConfigFile,
    MCPHubStatus,
    MCPNamespacedTool,
    MCPServerDefinition,
)


def test_mcp_hub_models_validation() -> None:
    """Verifica modelos Pydantic v2 de configuração e estado do MCP Hub."""
    server = MCPServerDefinition(
        command="python",
        args=["-m", "mcp_server_postgres"],
        env={"DB_URL": "postgresql://localhost:5432/db"},
        transport="stdio",
        max_failures=3,
        reset_timeout_seconds=20.0,
    )
    assert server.transport == "stdio"
    assert server.max_failures == 3
    assert server.env["DB_URL"] == "postgresql://localhost:5432/db"

    config = MCPConfigFile(
        mcpServers={
            "postgres": server,
            "github": MCPServerDefinition(
                transport="sse",
                url="https://api.github.com/mcp",
                bearer_token="ghp_test_token_123",
            ),
        }
    )
    assert len(config.mcpServers) == 2
    assert config.mcpServers["github"].transport == "sse"

    tool = MCPNamespacedTool(
        server_name="postgres",
        tool_name="query",
        namespaced_name="postgres.query",
        description="Executa queries SQL em modo read-only",
        input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
    )
    assert tool.namespaced_name == "postgres.query"

    status = MCPHubStatus(
        total_servers=2,
        active_servers=["postgres", "github"],
        circuit_states={"postgres": "CLOSED", "github": "CLOSED"},
        total_tools=5,
        tools_by_server={"postgres": 2, "github": 3},
    )
    assert status.total_servers == 2
    assert status.total_tools == 5


def test_mcp_hub_load_config_and_registration(tmp_path: Path) -> None:
    """Verifica o carregamento de arquivo de configuração .mcp.json."""
    mcp_json_content = {
        "mcpServers": {
            "postgres": {
                "command": "python",
                "args": ["-m", "servers.postgres"],
                "env": {"DATABASE_URL": "sqlite:///:memory:"},
            },
            "github": {
                "transport": "sse",
                "url": "https://mcp.github.corp/sse",
                "bearer_token": "token_abc_xyz",
            },
        }
    }
    config_file = tmp_path / ".mcp.json"
    config_file.write_text(json.dumps(mcp_json_content), encoding="utf-8")

    hub = MCPEnterpriseHub(config_path=config_file)
    status = hub.get_status()

    assert status.total_servers == 2
    assert "postgres" in status.active_servers
    assert "github" in status.active_servers
    assert status.circuit_states["postgres"] == CircuitState.CLOSED.value
    assert status.circuit_states["github"] == CircuitState.CLOSED.value

    # Registra ferramentas mockadas
    mock_tool_1 = MCPNamespacedTool(
        server_name="postgres",
        tool_name="select",
        namespaced_name="postgres.select",
        description="Executa SELECT no banco de dados",
    )
    mock_tool_2 = MCPNamespacedTool(
        server_name="github",
        tool_name="create_issue",
        namespaced_name="github.create_issue",
        description="Cria uma nova issue no repositório",
    )
    hub.register_tool(mock_tool_1)
    hub.register_tool(mock_tool_2)

    tools = hub.list_tools()
    assert len(tools) == 2
    assert any(t.namespaced_name == "postgres.select" for t in tools)
    assert any(t.namespaced_name == "github.create_issue" for t in tools)

    postgres_tools = hub.list_tools(server_filter="postgres")
    assert len(postgres_tools) == 1
    assert postgres_tools[0].namespaced_name == "postgres.select"


def test_mcp_hub_tool_resolution_and_calling() -> None:
    """Verifica despacho determinístico de execução de ferramentas por namespace."""
    hub = MCPEnterpriseHub()
    mock_handler = MagicMock(return_value={"rows": [{"id": 1, "name": "Admin"}]})

    hub.register_server(
        name="postgres",
        config=MCPServerDefinition(command="dummy"),
        handler=mock_handler,
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="postgres",
            tool_name="query",
            namespaced_name="postgres.query",
            description="Query no banco",
        )
    )

    result = hub.call_tool("postgres.query", arguments={"sql": "SELECT * FROM users"})
    assert result == {"rows": [{"id": 1, "name": "Admin"}]}
    mock_handler.assert_called_once_with("query", {"sql": "SELECT * FROM users"})

    # Falha ao chamar ferramenta inexistente
    with pytest.raises(KeyError):
        hub.call_tool("unregistered.tool")

    with pytest.raises(ValueError):
        hub.call_tool("invalid_tool_without_dot")


def test_mcp_hub_circuit_breaker_isolation() -> None:
    """Verifica isolamento de falhas: circuit breaker aberto em um servidor não afeta os outros."""
    hub = MCPEnterpriseHub()

    # Servidor que falha
    failing_handler = MagicMock(side_effect=RuntimeError("Timeout de conexão"))
    hub.register_server(
        name="jira",
        config=MCPServerDefinition(command="jira_mcp", max_failures=2),
        handler=failing_handler,
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="jira",
            tool_name="get_ticket",
            namespaced_name="jira.get_ticket",
            description="Obtém ticket",
        )
    )

    # Servidor saudável
    healthy_handler = MagicMock(return_value={"status": "ok"})
    hub.register_server(
        name="github",
        config=MCPServerDefinition(command="github_mcp"),
        handler=healthy_handler,
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="github",
            tool_name="ping",
            namespaced_name="github.ping",
            description="Ping no GitHub",
        )
    )

    # Induz 2 falhas no Jira para abrir o circuito
    with pytest.raises(RuntimeError):
        hub.call_tool("jira.get_ticket")
    with pytest.raises(RuntimeError):
        hub.call_tool("jira.get_ticket")

    # Circuito do Jira deve estar OPEN
    assert hub.get_status().circuit_states["jira"] == CircuitState.OPEN.value

    # Chamada ao Jira é bloqueada pelo Circuit Breaker imediatamente
    with pytest.raises(RuntimeError, match="Circuit breaker is OPEN"):
        hub.call_tool("jira.get_ticket")

    # Servidor do GitHub continua 100% operacional (Isolamento total)
    assert hub.get_status().circuit_states["github"] == CircuitState.CLOSED.value
    res = hub.call_tool("github.ping")
    assert res == {"status": "ok"}


def test_mcp_hub_system_one_tool_pruning() -> None:
    """Verifica a poda seletiva de ferramentas para context window usando o Sistema 1."""
    hub = MCPEnterpriseHub()

    tools = [
        MCPNamespacedTool(
            server_name="postgres",
            tool_name="select",
            namespaced_name="postgres.select",
            description="Executa consulta SELECT SQL na tabela de usuários ou clientes",
        ),
        MCPNamespacedTool(
            server_name="postgres",
            tool_name="insert",
            namespaced_name="postgres.insert",
            description="Insere novo registro no banco de dados",
        ),
        MCPNamespacedTool(
            server_name="github",
            tool_name="create_pr",
            namespaced_name="github.create_pr",
            description="Abre um Pull Request no repositório",
        ),
        MCPNamespacedTool(
            server_name="jira",
            tool_name="update_issue",
            namespaced_name="jira.update_issue",
            description="Atualiza status de issue no backlog",
        ),
        MCPNamespacedTool(
            server_name="aws",
            tool_name="s3_upload",
            namespaced_name="aws.s3_upload",
            description="Faz upload de arquivo para bucket S3",
        ),
    ]

    for t in tools:
        hub.register_tool(t)

    # Prompt relacionado a banco de dados
    pruned = hub.prune_tools_for_prompt(
        prompt="Preciso consultar a tabela de usuários no banco de dados",
        max_tools=2,
    )
    assert len(pruned) <= 2
    assert any(t.server_name == "postgres" for t in pruned)
    assert not any(t.server_name == "aws" for t in pruned)


def test_mcp_hub_cli_integration(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifica comandos da CLI corporativa mcp hub."""
    from corporate_engineer.cli import main

    mcp_config = {
        "mcpServers": {
            "sentry": {
                "command": "sentry-cli",
                "args": ["mcp"],
            }
        }
    }
    cfg_file = tmp_path / "test_mcp.json"
    cfg_file.write_text(json.dumps(mcp_config), encoding="utf-8")

    # CLI mcp hub list
    code = main(["mcp", "hub", "--config", str(cfg_file), "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "MCP ENTERPRISE HUB" in captured.out
    assert "sentry" in captured.out
