# PR: feat(mcp,orchestrator,quality): Onda P2 — SSE real, executores plugáveis no Swarm/DAG e auditoria AST de wiring (IMP-0037 / IMP-0038 / IMP-0039 / ADR-034)

## 📌 Resumo das Modificações
Implementação da **Onda P2** coordenada via Senior Swarm em conformidade com o **ADR-034**:

1. **Suporte Real a `text/event-stream` (`IMP-0037` — `src/corporate_engineer/mcp/client.py`)**:
   - Parser dual JSON / SSE (`_extract_content_type`, `_looks_like_sse`, `_extract_sse_events`, `_parse_sse_payload`, `_parse_response_payload`) suportando eventos `data:` multi-linha, comentários `:`, `[DONE]`, casamento de `id`, headers `MagicMock` e contabilização de erros no `CircuitBreaker`.
2. **Orquestração Plugável & Analisadores Determinísticos Reais (`IMP-0038` — `src/corporate_engineer/orchestrator/swarm.py`, `graph.py`)**:
   - `SwarmCoordinator`: protocolo `RoleExecutor`, parâmetros `workspace_path` / `role_executor`, analisadores locais reais por papel (`CanonicalSecretScanner`, `SemanticCodeEvaluator`, `CachedASTCodebaseIndexer`, `CapabilityWiringAuditor`), argumentos contextuais para ferramentas MCP, sinalização de `execution_mode` e consenso `REJECTED` honesto.
   - `AutonomousEngineeringGraph.run_pipeline()`: parâmetro `code_executor` plugável e `details["execution_mode"]` (`"deterministic-pipeline"` vs `"custom-code-executor"`).
3. **Auditoria de Wiring via AST Real (`IMP-0039` — `src/corporate_engineer/quality/wiring_auditor.py`)**:
   - Substituição de busca por substring por indexação AST de testes (`TestASTReferences`, `ast.Import`, `ast.ImportFrom`, `ast.Name`, `ast.Attribute` e defs `test_*`/`Test*`), eliminando falsos positivos em comentários e strings.

---

## 🧪 Plano de Testes & Validação

- [x] Shift-Left TDD (`tests/test_mcp_client.py`, `tests/test_swarm_coordinator.py`, `tests/test_autonomous_runner.py`, `tests/test_auto_wiring_integrity.py`).
- [x] Pre-Flight Gate verificado (`staff-verifier`):
  - `ruff check .`: 0 erros (`All checks passed!`)
  - `ruff format --check .`: 0 erros (`179 files already formatted`)
  - `mypy .`: 0 erros (`104 source files`)
  - `secret_scanner.py .`: `PASS` (`0` segredos)
  - `corporate-engineer audit --wiring`: `PASS`
  - `pytest -q`: **403 passed in 441.29s**
