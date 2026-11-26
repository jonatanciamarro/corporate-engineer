# ADR-034: SSE Real no Cliente MCP, Executores Plugáveis no Swarm/DAG & Auditoria AST de Wiring (Onda P2: IMP-0037 + IMP-0038 + IMP-0039)

## Status
Aceito (Accepted) — Aguardando Gate 1 do `corp-pipeline` para Execução

## Data
2026-11-26

## Contexto & Motivação
A Onda P2 eleva a profundidade arquitetural e a fidelidade operacional de três subsistemas centrais:

1. **Suporte Real a `text/event-stream` (SSE) (`IMP-0037` — `src/corporate_engineer/mcp/client.py`)**:
   `RemoteMCPSSEClient._send_request()` envia `Accept: application/json, text/event-stream`, mas realiza apenas `json.loads(raw_bytes)` direto sobre a resposta HTTP, falhando quando servidores MCP retornam payloads no formato SSE (`event: message\ndata: {...}\n\n`).
2. **Stubs Estáticos em Orquestração (`IMP-0038` — `src/corporate_engineer/orchestrator/swarm.py` & `graph.py`)**:
   - `SwarmCoordinator.dispatch_task()` retorna strings fixas de `ROLE_SPECIALIZATIONS` e invoca ferramentas MCP com `{}` sem análise real do workspace ou contexto.
   - `AutonomousEngineeringGraph.run_pipeline()` grava código placeholder em memória na fase `IMPLEMENT` sem explicitar `execution_mode` ou permitir injeção de executor plugável.
3. **Auditoria de Wiring por Substring (`IMP-0039` — `src/corporate_engineer/quality/wiring_auditor.py`)**:
   `CapabilityWiringAuditor.audit()` verifica cobertura indireta por busca textual simples (`mod_stem in t_content or any(s in t_content for s in symbols)`), permitindo falsos positivos quando um nome aparece apenas em comentário ou string literal.

## Decisão de Arquitetura

### 1. Parser Dual JSON / `text/event-stream` em `RemoteMCPSSEClient` (`IMP-0037`)
- Extrair helper `_parse_response_payload(raw_text: str, content_type: str = "") -> dict[str, Any]`:
  - Se `content_type` indicar `text/event-stream` ou o corpo não for JSON direto e contiver linhas `data:`/`event:`, parsear eventos SSE separados por linha em branco (suportando múltiplas linhas `data:` concatenadas por `\n`, ignorando comentários `:` e `data: [DONE]`).
  - Priorizar o frame JSON-RPC correspondente ao `id` da requisição ou o último evento JSON-RPC válido contendo `"result"` ou `"error"`.
  - Manter fallback para `json.loads(raw_text)` quando `application/json` ou mock simples em testes.

### 2. Executores Plugáveis & Analisadores Locais Reais (`IMP-0038`)
- **`SwarmCoordinator` (`orchestrator/swarm.py`)**:
  - Definir protocolo/assinatura `RoleExecutor = Callable[[SwarmMember, str, list[dict[str, Any]]], str]` aceito opcionalmente em `__init__(..., workspace_path: Path | str = ".", role_executor: RoleExecutor | None = None)`.
  - Por padrão (`role_executor is None`), executar **analisadores locais determinísticos reais** sobre `workspace_path` de acordo com o papel:
    - `security-reviewer`: executa `CanonicalSecretScanner` reportando quantidade real de achados.
    - `code-reviewer` / `python-reviewer`: executa `SemanticCodeEvaluator` reportando nota composta e violações.
    - `rag-pipeline-reviewer`: consulta `CachedASTCodebaseIndexer` reportando total real de símbolos/arquivos indexados.
    - `architect`: executa `CapabilityWiringAuditor` reportando taxa real de módulos conectados.
    - Outros papéis (`tdd-guide`, `build-error-resolver`, `refactor-cleaner`, etc.): sintetizam inspeção estruturada incorporando resultados reais das ferramentas MCP executadas.
  - Expor `execution_mode` (`"custom-executor"` vs `"deterministic-analyzer"`) nas recomendações/metadados do `SwarmGoalReport`.
- **`AutonomousEngineeringGraph.run_pipeline()` (`orchestrator/graph.py`)**:
  - Aceitar `code_executor: Callable[[str, RevisedPromptSpec], list[CodeDiff] | str] | None = None` em `run_pipeline()` (com default `None`).
  - Quando `code_executor` for fornecido, registrar os diffs retornados via `step_implement`; quando `None`, manter modo determinístico explícito registrando `details["execution_mode"] = "deterministic-pipeline"` (versus `"custom-code-executor"`) sem simular geração por IA.

### 3. Auditoria de Referências via AST em `CapabilityWiringAuditor` (`IMP-0039`)
- Substituir a busca por substring em `_get_test_contents()` por extração AST (`_extract_test_references()`) que coleta exclusivamente:
  - Módulos importados (`ast.Import`, `ast.ImportFrom.module` e aliases/nomes importados).
  - Referências reais em código (`ast.Name.id`, `ast.Attribute.attr`), ignorando completamente comentários e literais `ast.Constant` de string.
- Preservar `has_direct_test` quando `tests/test_<mod_stem>.py` existir e definir ao menos uma função de teste (`test_*`).

## Consequências
- **Positivas**: Compatibilidade real com servidores MCP via SSE, pareceres concretos baseados em métricas reais do repositório no Swarm, transparência explícita do modo de execução no pipeline e eliminação de falsos positivos por substring no `CapabilityWiringAuditor`.
- **Riscos e Mitigações**: `SemanticCodeEvaluator` ou `CanonicalSecretScanner` em `SwarmCoordinator` precisam respeitar diretórios ignorados (`.venv`, `.git`) para manter latência baixa; testes existentes de `SwarmCoordinator` que não passam `workspace_path` rodarão rápido em `"."` ou diretório configurado.
