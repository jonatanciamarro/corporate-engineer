# PR-CORP-027: Conexão Total de Módulos Desconectados, Unificação de Cache AST SHA-256 e Enriquecimento E2E do run_pipeline

## Tipo de Mudança
- [x] `feat`: Integração de ponta a ponta dos motores do framework em `run_pipeline`, unificação do cache AST SHA-256 e exportações públicas no top-level
- [x] `refactor`: Canonização de `CanonicalSecretScanner` como Single Source of Truth para credenciais em gates, hooks e ferramentas
- [x] `test`: Novos testes automatizados Shift-Left TDD (`tests/test_connected_e2e_pipeline.py`)
- [x] `docs`: Formalização do ADR-025

## Ticket / ID da Proposta
- **ID**: `IMP-0027`
- **Referência ADR**: [ADR-025](../../docs/adr/ADR-025-connect-disconnected-modules-and-e2e-pipeline.md)
- **Status do Backlog**: `IMPLEMENTED`

---

## Descrição do Pull Request

Este Pull Request implementa a resolução estrutural de integração sistêmica identificada pelo Swarm Max, eliminando desconexões e redundâncias entre os motores autônomos desenvolvidos ao longo das 25 melhorias anteriores:

1. **Unificação do Cache AST SHA-256 e Análise em Lote (`src/corporate_engineer/rag/`)**:
   - `CachedASTCodebaseIndexer` passa a fornecer `get_file_symbols` e `get_all_symbol_names` com cache SHA-256 persistente.
   - `BlastRadiusAnalyzer` inicializa nativamente com `CachedASTCodebaseIndexer`, eliminando re-leituras de disco com `ast.parse` redundante.
   - Adição do método de lote `analyze_files(file_paths: Sequence[str | Path], max_depth: int = 3) -> BlastRadiusReport`, permitindo que múltiplos arquivos alterados sejam analisados em uma única passada unificada BFS.
   - `ContextAwarePromptRefiner.find_ast_symbols()` passa a consultar o conjunto de símbolos do `CachedASTCodebaseIndexer`, atingindo resolução $O(1)$ em memória.

2. **Canonização de Scanner de Segredos e Quality Gate (`src/corporate_engineer/quality/`)**:
   - Criação de `CanonicalSecretScanner` em `src/corporate_engineer/quality/secret_scanner.py` como Single Source of Truth para detecção de credenciais (10 padrões de alta confiança).
   - Refinamento de `SAFE_PLACEHOLDERS` para evitar falsos-positivos em chaves de teste (`AKIA...`).
   - `QualityGateRunner.run_secret_scan()` passa a delegar formalmente para `self.secret_scanner.scan_directory(self.project_root)`.
   - `SurgicalTestRunner` atualizado para agrupar arquivos Python modificados e invocar `analyze_files` em lote.
   - Unificação de `tool_security_guard.py` e `.agents/skills/.../secret_scanner.py` consumindo `CanonicalSecretScanner`.

3. **Amarração E2E Completa em `AutonomousEngineeringGraph.run_pipeline` (`src/corporate_engineer/orchestrator/graph.py`)**:
   - **PLANNING**: Aciona `ProactiveAnticipator` para formular o plano `AnticipationPlan` (com passos 1 e 2) e salva em `details["anticipation_plan"]`.
   - **TDD**: Aciona `SurgicalTestRunner` para identificar testes afetados e integrá-los aos cenários TDD.
   - **IMPLEMENT**: Aciona `ASTSelfHealingFixer` para auto-remediação sintática e formatação pós-escrita com relatório em `details["ast_fix_report"]`.
   - **AUDIT**: Aciona `SemanticCodeEvaluator` (scorecard EDD de conformidade estrutural) junto ao `QualityGateRunner`.
   - **DELIVER**: Invoca `corporate_engineer.git_utils.generate_pr_url` com garantia de push remoto e injeta `pr_url` em `details["pr_url"]`.

4. **Public API Exports Canônicos (`src/corporate_engineer/__init__.py`)**:
   - Exportação formal e registro em `__all__` dos 8 componentes centrais:
     `AutonomousEngineeringGraph`, `ProactiveAnticipator`, `QualityGateRunner`, `BlastRadiusAnalyzer`, `CachedASTCodebaseIndexer`, `SurgicalTestRunner`, `ASTSelfHealingFixer`, `CanonicalSecretScanner`.

5. **Suíte Abrangente de Shift-Left TDD (`tests/test_connected_e2e_pipeline.py`)**:
   - 8 novos testes de integração e unitários cobrindo exportações públicas, helpers de cache AST, injeção em blast radius, análise em lote, refiner O(1), scanner canônico e pipeline E2E completo.
   - Suíte global expandida para **278/278 testes PASS** em 47.37s.

---

## Verificações de Pre-Flight (100% Aprovadas)

- [x] **Testes Automatizados**: `pytest` (278/278 PASS)
- [x] **Linter & Formatação**: `ruff check .` e `ruff format --check .` (0 erros em 141 arquivos)
- [x] **Tipagem Estática**: `mypy .` (0 erros em 82 arquivos)
- [x] **Pre-Flight Secret Scan**: `secret_scanner.py` (0 vazamentos)
