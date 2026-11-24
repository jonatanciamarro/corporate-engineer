# ADR-030: Resiliência de Concorrência, Sincronização & Eliminação de Erros Silenciosos (IMP-0030)

## Status
Aceito (Accepted)

## Data
2026-11-24

## Contexto & Motivação
A auditoria técnica profunda realizada pelo Swarm Sênior de 5 especialistas revelou vulnerabilidades críticas em protocolos e concorrência no framework `corporate-engineer`:

1. **Falsificação de Branch Pushed no Git (`git_utils.py:158-171`)**:
   Em `is_branch_pushed()`, se `git rev-parse target_branch` falhava com exit code não-zero (ex: referência local ausente ou corrompida), o fluxo caía no `return True` final, certificando erroneamente que a branch estava no remote e violando a Invariante 8. Além disso, a busca por `git ls-remote --heads` usava `split()[0]`, podendo casar branches com mesmo prefixo.
2. **Inversão de Erro no Cliente MCP SSE (`mcp/client.py:255-273`)**:
   `RemoteMCPSSEClient.call_tool()` lia `is_error` exclusivamente dentro de `res.get("result", {})`. No protocolo JSON-RPC 2.0, erros de servidor vêm na chave raiz `error`. Com isso, falhas fatais no servidor MCP eram mascaradas como execuções bem-sucedidas (`is_error=False`).
3. **Falso Sucesso em Execução do Swarm (`orchestrator/swarm.py:95-133, 189-196`)**:
   Em `dispatch_task()`, `success = True` nunca era alterado para `False` caso a ferramenta MCP reportasse erro ou lançasse exceção. Na agregação `run_fan_out()`, a tarefa com erro era contabilizada como sucesso, aprovando deliberações multi-agente (`APPROVED`) mesmo com falhas de ferramentas.
4. **Vazamento de Contexto de Telemetria entre Coroutines (`telemetry/tracer.py:44-56`)**:
   O `AgentTracer` gerenciava a pilha `_active_stack` via `threading.local()`. Em loops assíncronos (`asyncio`), múltiplas coroutines executando na mesma thread do SO compartilhavam a mesma pilha de spans, corrompendo hierarquias pai-filho e cálculos de tokens.
5. **Race Conditions e Falta de Sincronização no Hub MCP (`mcp/hub.py:22-147`)**:
   O `MCPEnterpriseHub` não possuía travas de concorrência, gerando `RuntimeError: dictionary changed size during iteration` durante acessos concorrentes em execuções paralelas de múltiplos agentes.
6. **Reentrância de Travas no SwarmCoordinator (`orchestrator/swarm.py:44`)**:
   O `SwarmCoordinator` utilizava `threading.Lock()` comum ao invés de `threading.RLock()`, arriscando deadlocks reentrantes.

## Decisão de Arquitetura

Decidiu-se implementar o **Pacote 1 de Blindagem Estrutural** abrangendo os 5 subsistemas afetados:

### 1. Robustez em `git_utils.py`
- Em `is_branch_pushed()`:
  - Validar explicitamente `proc_head.returncode != 0`, retornando `False` com warning estruturado.
  - No parsing do `git ls-remote`, casar estritamente a referência completa `f"refs/heads/{target_branch}"` ao invés de extrair cegamente a primeira linha.
  - Aplicar timeouts padronizados em `get_current_branch()`, `get_remote_url()` e `generate_pr_url()`.

### 2. Tratamento Correto do Envelope JSON-RPC 2.0 em `mcp/client.py`
- Inspecionar a chave raiz `error` na resposta de `call_tool()`:
  - Se `"error" in res`: extrair mensagem e código, definir `is_error = True` e registrar explicitamente a falha no `CircuitBreaker`.
- Execução segura em `LocalMCPToolAdapter`: sanitizar chamada com `shell=False` e `shlex.split`.

### 3. Confiabilidade e Governança no `orchestrator/swarm.py`
- Em `SwarmCoordinator`: migrar `self._lock` para `threading.RLock()`.
- Em `dispatch_task()`: atribuir `success = False` imediatamente quando `res.is_error == True` ou em qualquer exceção capturada.
- Em `run_fan_out()`: verificar `(not r.success or bool(r.error))` para computar tarefas falhas e reprovar o consenso se houver falhas críticas.
- Assegurar preservação das ferramentas MCP nos membros durante chamadas em leque (fan-out).

### 4. Isolamento Async de Spans via `contextvars.ContextVar` em `telemetry/tracer.py`
- Substituir `threading.local` por `contextvars.ContextVar("active_span_stack", default=None)`.
- Garantir isolamento perfeito da pilha de spans por coroutine e thread, prevenindo contaminação cruzada.
- Em `export_trace()`: calcular a duração total pela envoltória temporal (`max(end) - min(start)`) e evitar contagem duplicada de tokens de spans pai em spans filho.

### 5. Sincronização Thread-Safe em `mcp/hub.py`
- Adicionar `self._lock = threading.RLock()` em `MCPEnterpriseHub` cobrindo registro de ferramentas, listagem, poda por prompt e disparo de chamadas.

## Consequências

### Positivas:
- **Zero Falsos Sucessos**: Falhas de ferramentas MCP, erros de branch e quebras operacionais são reportados com precisão fidedigna.
- **Async & Thread-Safety Completo**: Telemetria OTel e Hub MCP tornam-se 100% seguros para paralelismo concorrente (threads e coroutines asyncio).
- **Conformidade Git Inegociável**: A Invariante 8 de push remoto fica blindada contra corrupções ou referências de branch inexistentes.

### Trade-offs:
- Migração para `ContextVar` exige controle cuidadoso de cópia de contexto caso coroutines sejam despachadas via threads externas.
