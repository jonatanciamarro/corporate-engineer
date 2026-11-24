# PR: feat(concurrency): concurrency resilience, synchronization and silent error elimination (IMP-0030 / ADR-030)

## 📌 Resumo das Modificações
Implementação do **Pacote 1 de Blindagem Estrutural** no framework `corporate-engineer`, sanando vulnerabilidades críticas identificadas pelo Swarm Sênior de Auditoria em protocolos de rede, concorrência thread/async e omissão de erros operacionais, em conformidade com o **ADR-030**:

1. **Eliminação de Falso Positivo em `git_utils.is_branch_pushed()`**:
   - Correção do fluxo de erro quando `git rev-parse` local falha (retornava `True` indevidamente, agora retorna `False` com warning).
   - Correspondência exata da referência `refs/heads/{target_branch}` no `git ls-remote --heads`, evitando casamento indevido com branches que compartilham o mesmo prefixo.
   - Aplicação de timeout configurável (`DEFAULT_GIT_TIMEOUT`) em `get_current_branch()` e `get_remote_url()`.

2. **Detecção e Tratamento Estrito de Erros JSON-RPC 2.0 no Cliente MCP (`mcp/client.py`)**:
   - `RemoteMCPSSEClient.call_tool()` agora inspeciona a chave raiz `error` na resposta JSON-RPC 2.0.
   - Em caso de erro de protocolo, retorna `MCPToolResult(is_error=True)` com a mensagem e registra a falha no `CircuitBreaker`.

3. **Correção de Falso Sucesso no Swarm Coordinator (`orchestrator/swarm.py`)**:
   - `dispatch_task()`: `success = False` é agora atribuído imediatamente sempre que a ferramenta chamada reportar erro (`res.is_error == True`) ou lançar exceção.
   - `run_fan_out()`: cálculo de tarefas bem-sucedidas valida `r.success and not r.error`, reprovando o consenso (`REJECTED`) em caso de falhas de ferramentas.
   - Migração da trava interna `self._lock` de `threading.Lock` para `threading.RLock` (ADR-021 re-entrância).
   - Suporte à preservação de ferramentas MCP específicas para cada subtask em `run_fan_out()`.

4. **Isolamento Async via `contextvars.ContextVar` no `AgentTracer` (`telemetry/tracer.py`)**:
   - Migração da pilha ativa `_active_stack` de `threading.local()` para `contextvars.ContextVar`.
   - Eliminação completa de vazamento de contexto e corrupção de hierarquia pai-filho entre coroutines assíncronas concorrentes executadas na mesma thread.

5. **Sincronização Thread-Safe com RLock no `MCPEnterpriseHub` (`mcp/hub.py`)**:
   - Inclusão de `self._lock = threading.RLock()` cobrindo registro de servidores e ferramentas, listagem, poda semântica e execução protegida.

6. **Shift-Left TDD (`tests/test_concurrency_resilience_and_silent_errors.py`)**:
   - 8 novos testes automatizados unitários e de integração validando cada cenário de falha antes da implementação e comprovando 100% de sucesso pós-remediação.
   - Suíte global expandida para **309/309 testes PASS** em 46.50s.

---

## 🧪 Plano de Testes & Validação

- [x] Teste de falha de rev-parse local em `is_branch_pushed` (`test_git_utils_is_branch_pushed_fails_when_local_branch_invalid`)
- [x] Teste de matching exato de ref no ls-remote (`test_git_utils_is_branch_pushed_matches_exact_ref_not_prefix`)
- [x] Teste de detecção de erro no envelope raiz JSON-RPC 2.0 no MCP client (`test_mcp_client_call_tool_handles_jsonrpc_root_error`)
- [x] Teste de atribuição de `success=False` em falha de ferramenta no Swarm (`test_swarm_dispatch_task_sets_success_false_on_tool_error`)
- [x] Teste de cálculo preciso de tarefas falhas no Fan-Out (`test_swarm_run_fan_out_computes_failed_tasks_accurately`)
- [x] Teste de uso de `RLock` re-entrante no `SwarmCoordinator` (`test_swarm_coordinator_uses_reentrant_lock`)
- [x] Teste de trava e segurança concorrente no `MCPEnterpriseHub` (`test_mcp_hub_uses_rlock_and_is_thread_safe`)
- [x] Teste de isolamento assíncrono de spans com coroutines concorrentes (`test_agent_tracer_async_context_isolation`)
- [x] Pre-Flight Gate 100% verde:
  - `pytest`: 309/309 PASS em 46.50s
  - `ruff check .`: 0 erros em 170 arquivos
  - `ruff format --check .`: 0 erros de formatação
  - `mypy .`: 0 erros em 102 arquivos
  - `secret_scanner.py`: 0 credenciais detectadas
  - `corporate-engineer audit --wiring`: PASS (100% dos módulos conectados)
