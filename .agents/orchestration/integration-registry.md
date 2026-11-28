# Registro de Integrações e MCPs (`integration-registry.md`)

> **Catálogo de Servidor/Clientes MCP, Plugins, Hooks e Integrações Git**  
> *Mapeamento de protocolos de integração, transportes, políticas de menor privilégio e requisitos do runtime Antigravity.*

---

## 1. Servidor e Clientes MCP do Sistema (`src/corporate_engineer/mcp/`)

O framework implementa tanto conectores quanto um servidor MCP `stdio` nativo com validação rígida via Pydantic v2:

| Componente / Transporte | Classe / Módulo | Protocolo Suportado | Status Operacional | Recursos & Segurança |
|---|---|---|---|---|
| **MCP Stdio Server Nativo** | `CorporateEngineerMCPServer` (`mcp/server.py`) | JSON-RPC 2.0 newline-delimited via `stdin`/`stdout` | `AVAILABLE` (`IMP-0042`) | Política read/audit por padrão (`allow_mutations=False`); expõe `blast_radius`, `eval_scorecard`, `audit_wiring`, `secret_scan`, `surgical_tests_plan`, `ast_symbols`; confinamento de caminhos e logs em `stderr`. |
| **MCP Stdio Client** | `StdioMCPClient` (`mcp/client.py`) | JSON-RPC 2.0 via `stdin`/`stdout` de subprocessos | `AVAILABLE` | Isolamento em processo filho (`shell=False`, `shlex.split`); timeout configurável; extração tipada de schemas. |
| **MCP SSE Remoto** | `RemoteMCPSSEClient` (`mcp/client.py`) | Server-Sent Events (`text/event-stream`) / JSON-RPC 2.0 HTTP | `AVAILABLE` | Bearer Tokens, headers corporativos (`X-Corporate-*`), parsing multi-linha SSE e `CircuitBreaker`. |
| **MCP Enterprise Hub** | `MCPEnterpriseHub` (`mcp/hub.py`) | Pools `.mcp.json` com multiplexação | `AVAILABLE` | Sincronização `RLock`, circuit breaker por ferramenta e poda semântica via System-One. |

### Execução e Validação MCP via CLI:
```powershell
# Iniciar servidor MCP stdio nativo (read/audit mode por padrão):
.venv\Scripts\python -m corporate_engineer.cli mcp serve --workspace .

# Teste de ping e schemas de ferramentas externas:
.venv\Scripts\python -m corporate_engineer.cli mcp ping --transport stdio --command "python -m dummy_server"
.venv\Scripts\python -m corporate_engineer.cli mcp list-tools --transport sse --url "https://mcp.internal.corp/events"
```

---

## 2. Servidores MCP e Hooks no Ambiente Antigravity

- **Plugin Workspace (`corporate-engineer`)**:
  - Manifesto: `.agents/plugins/corporate-engineer/plugin.json`
  - Configuração MCP: `.agents/plugins/corporate-engineer/mcp_config.json`
  - Expõe nativamente o servidor `corporate-engineer` via `stdio` (`mcp serve`) conforme a especificação de plugins e MCP do Antigravity (`agy-customizations`).
- **Configuração Global (Opcional)**: `~/.gemini/config/mcp_config.json`.
- **Lifecycle Hooks (`.agents/hooks.json`)**:
  - Os 5 hooks (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`) usam `.agents/orchestration/hooks/run_hook.py` com `timeout: 15` e fallback portável de interpretador (`py` → `python3` → `python`), permitindo execução limpa no Windows via `cmd /c` (onde apenas `py` e `.venv\Scripts\python.exe` existem por padrão) e em ambientes POSIX (`sh -c`).
  - **Requisito de Trusted Workspace**: No Antigravity, hooks definidos no workspace (`.agents/hooks.json`) exigem que o workspace esteja marcado como **Trusted** para disparo automático pela IDE/CLI.

---

## 3. Plugins e Integrações do Marketplace

O ecossistema Antigravity suporta plugins oficiais e de parceiros. O status de autenticação deve ser sempre verificado via `list_plugin_accounts` antes de operações que exigem credenciais.

| Categoria | Plugins em Destaque | Status | Fronteira de Permissão |
|---|---|---|---|
| **Workspace Core** | `corporate-engineer` (`.agents/plugins/corporate-engineer/`) | `AVAILABLE` | Read/Audit por padrão (`allow_mutations=False`); mutações requerem `--allow-mutations`. |
| **Google Workspace** | `gdocs`, `gsheets`, `gslides` | `AVAILABLE_VIA_MARKETPLACE` | Leitura e escrita sob demanda; requer autenticação da conta Google. |
| **Developer Tools** | `chrome-devtools-plugin`, `android-cli-plugin` | `AVAILABLE_VIA_MARKETPLACE` | Depuração via Puppeteer e Android SDK. |
| **Cloud Hosting** | `netlify`, `railway` | `AVAILABLE_VIA_MARKETPLACE` | Deploy, monitoramento e inspeção de logs. Operações de deploy exigem Gate 2. |
| **Project Tracking** | `linear`, `atlassian-twg-cli` | `AVAILABLE_VIA_MARKETPLACE` | Sincronização de tickets e issues. |

---

## 4. Integração Remota Git & GitHub CLI

- **Repositório Remoto**: `origin` (`https://github.com/jonatanciamarro/corporate-engineer.git`).
- **Automação de PR**: Script `.agents/skills/corp-pipeline/scripts/pr_automator.py` e `git_utils.py` interagem com Git e GitHub CLI (`gh`).
- **Ambientes Windows Sandbox (`dubious ownership`)**: Comandos manuais de inspeção devem usar `git -c "safe.directory=*" ...` quando o diretório pertencer a outro SID; ferramentas internas (`SurgicalTestRunner`, `git_utils.py`) tratam `exit 128` sem cascata de erro.
- **Regra de Proteção**: Proibido push direto na branch `main`. Todo código de feature deve ser submetido via branch `feat/<TICKET_ID>-<slug>` ou `fix/<TICKET_ID>-<slug>` com `git push -u origin <branch>` obrigatório antes de gerar links de PR.
