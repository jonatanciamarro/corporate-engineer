# ADR-011: MCP Enterprise Hub & Tool Multiplexer (.mcp.json Pools & System-One Pruning)

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
O Model Context Protocol (MCP) se consolidou como o padrão de interoperabilidade entre agentes de IA e ferramentas externas. No framework `corporate-engineer`, os clientes MCP originais (`LocalMCPToolAdapter` e `RemoteMCPSSEClient`) gerenciavam apenas uma conexão isolada por vez, sem suporte nativo para orquestrar múltiplos servidores corporativos simultaneamente (ex.: GitHub, Jira, Postgres, Sentry, AWS).

Além disso, em ambientes empresariais com dezenas de ferramentas MCP configuradas em arquivos padrão como `.mcp.json`, injetar todas as definições de ferramentas no contexto do LLM (System Two) causa:
1. Alto consumo e desperdício de tokens na context window;
2. Degradação de atenção e aumento na taxa de alucinação na seleção de ferramentas;
3. Ausência de isolamento de falhas: se um servidor externo falha, todo o ecossistema é impactado.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `MCPServerDefinition`: Especificação do servidor MCP com transporte (`stdio` ou `sse`), comando, argumentos, variáveis de ambiente, URL remota, token de autenticação e parâmetros de Circuit Breaker.
   - `MCPConfigFile`: Modelo que reflete o schema canônico do `.mcp.json` (`mcpServers`).
   - `MCPNamespacedTool`: Representação de ferramenta com namespace unificado (`server_name.tool_name`), descrição e schema de entrada.
   - `MCPHubStatus`: Relatório de observabilidade com servidores ativos, status de circuit breakers e contagem de ferramentas.

2. **Motor `MCPEnterpriseHub` (`src/corporate_engineer/mcp/hub.py`)**:
   - Gerenciamento unificado de conexões multi-servidor carregadas de arquivos `.mcp.json` ou registradas programaticamente.
   - **Isolamento de Falhas com Circuit Breakers Individuais**: Cada servidor conectado possui sua própria instância de `CircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`), impedindo que lentidões no Jira ou Postgres bloqueiem comandos no GitHub.
   - **Namespace Unificado**: Resolução determinística no formato `<servidor>.<ferramenta>` (ex.: `github.create_pr`, `postgres.query_read_only`).
   - **Poda Inteligente via Sistema 1 (`prune_tools_for_prompt`)**: Utiliza o motor de decisões reflexivas do Sistema 1 para selecionar apenas as 2 a 5 ferramentas mais relevantes para o prompt, economizando mais de 80% dos tokens de ferramentas.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer mcp hub`:
     - `--config <path>`: Carrega o arquivo `.mcp.json`.
     - `list`: Lista ferramentas unificadas por namespace e status de conectividade.
     - `call <tool>`: Invoca a ferramenta especificada com argumentos em JSON.
     - `prune --prompt <text>`: Demonstra a seleção seletiva do Sistema 1.

## Consequências
- **Positivas**:
  - Plataforma única para conectar múltiplos ecossistemas empresariais via MCP.
  - Zero alucinação por saturação de ferramentas através da poda do Sistema 1.
  - Resiliência corporativa com proteção contra falhas em cascata via Circuit Breaker.
  - Compatibilidade com o ecossistema padrão (.mcp.json do VS Code, Cursor e Claude).
- **Mitigações**:
  - Fallback transparente caso um servidor falhe ou abra o circuito, retornando erro estruturado sem derrubar a execução do agente.
