"""
MCP Enterprise Hub & Tool Multiplexer (.mcp.json multi-server pools) (IMP-0011).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from corporate_engineer.mcp.circuit_breaker import CircuitBreaker
from corporate_engineer.models import (
    MCPConfigFile,
    MCPHubStatus,
    MCPNamespacedTool,
    MCPServerDefinition,
)


class MCPEnterpriseHub:
    """Hub corporativo unificado para orquestação de múltiplos servidores MCP."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.servers: dict[str, MCPServerDefinition] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.handlers: dict[str, Callable[[str, dict[str, Any]], Any]] = {}
        self.tools: dict[str, MCPNamespacedTool] = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_source: str | Path | dict[str, Any]) -> None:
        """Carrega e instancia servidores definidos em arquivo .mcp.json ou dicionário."""
        raw_data: dict[str, Any]
        if isinstance(config_source, (str, Path)):
            path = Path(config_source).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de configuração MCP não encontrado: {path}")
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        else:
            raw_data = config_source

        config = MCPConfigFile.model_validate(raw_data)
        for name, server_def in config.mcpServers.items():
            if server_def.enabled:
                self.register_server(name, server_def)

    def register_server(
        self,
        name: str,
        config: MCPServerDefinition,
        handler: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        """Registra um servidor no pool com seu respectivo Circuit Breaker isolado."""
        self.servers[name] = config
        self.circuit_breakers[name] = CircuitBreaker(
            failure_threshold=config.max_failures,
            recovery_timeout=config.reset_timeout_seconds,
        )
        if handler:
            self.handlers[name] = handler
        else:
            # Handler padrão simulado / stub
            def _default_handler(tool: str, args: dict[str, Any]) -> dict[str, Any]:
                return {"status": "ok", "server": name, "tool": tool, "args": args}

            self.handlers[name] = _default_handler

    def register_tool(self, tool: MCPNamespacedTool) -> None:
        """Registra uma ferramenta sob o namespace <server>.<tool>."""
        self.tools[tool.namespaced_name] = tool

    def list_tools(self, server_filter: str | None = None) -> list[MCPNamespacedTool]:
        """Lista ferramentas registradas com filtro opcional por servidor."""
        if server_filter:
            return [t for t in self.tools.values() if t.server_name == server_filter]
        return list(self.tools.values())

    def call_tool(
        self,
        namespaced_tool: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executa a ferramenta sob isolamento de falha via Circuit Breaker individual."""
        if "." not in namespaced_tool:
            raise ValueError(
                f"Ferramenta '{namespaced_tool}' deve seguir o padrão namespaced '<server>.<tool>'"
            )

        server_name, tool_name = namespaced_tool.split(".", 1)
        if namespaced_tool not in self.tools:
            raise KeyError(f"Ferramenta '{namespaced_tool}' não registrada no hub MCP")

        if server_name not in self.servers or server_name not in self.handlers:
            raise KeyError(f"Servidor '{server_name}' não registrado ou indisponível")

        breaker = self.circuit_breakers[server_name]
        handler = self.handlers[server_name]
        args = arguments or {}

        # Execução protegida por Circuit Breaker individual
        return breaker.execute(handler, tool_name, args)

    def prune_tools_for_prompt(
        self,
        prompt: str,
        max_tools: int = 5,
    ) -> list[MCPNamespacedTool]:
        """Utiliza o Sistema 1 para selecionar as ferramentas mais prováveis, poupando context window."""
        if not self.tools:
            return []

        prompt_tokens = set(re.findall(r"\b\w+\b", prompt.lower()))

        scored_tools: list[tuple[float, MCPNamespacedTool]] = []
        for tool in self.tools.values():
            tool_text = f"{tool.server_name} {tool.tool_name} {tool.description}".lower()
            tool_tokens = set(re.findall(r"\b\w+\b", tool_text))
            matches = prompt_tokens.intersection(tool_tokens)

            # Bônus por correspondência exata de servidor
            server_bonus = 3.0 if tool.server_name.lower() in prompt_tokens else 0.0
            score = len(matches) * 2.0 + server_bonus

            scored_tools.append((score, tool))

        # Ordena por score decrescente
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [tool for _, tool in scored_tools[:max_tools]]

    def get_status(self) -> MCPHubStatus:
        """Retorna o status consolidado de saúde e governança de todo o pool de servidores."""
        active = list(self.servers.keys())
        states = {s: self.circuit_breakers[s].state.value for s in active}
        tools_count: dict[str, int] = {}
        for t in self.tools.values():
            tools_count[t.server_name] = tools_count.get(t.server_name, 0) + 1

        return MCPHubStatus(
            total_servers=len(active),
            active_servers=active,
            circuit_states=states,
            total_tools=len(self.tools),
            tools_by_server=tools_count,
        )
