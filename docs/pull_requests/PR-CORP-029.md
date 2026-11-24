# PR: feat(quality): continuous capability auto-wiring and maximum power invariant (IMP-0029 / ADR-029)

## 📌 Resumo das Modificações
Implementação da **Invariante Arquitetural de Auto-Conexão e Verificação Contínua de Potência Máxima (Always-On Auto-Wiring)** no framework `corporate-engineer`, assegurando a erradicação definitiva de "código órfão" (*disconnected module debt*) e garantindo que toda nova funcionalidade seja automaticamente conectada nos 5 elos obrigatórios (DTOs, exportação pública, CLI, prompt refiner e pipeline autônomo), em conformidade estrita com o **ADR-029** e a filosofia do usuário (*"garantir que toda nova implementação já esteja conectada e funcionando automaticamente potência máxima 100%"*):

1. **Invariante 9 Estabelecida nas Diretrizes do Repositório (`AGENTS.md`, `GEMINI.md`, `corporate-quality-gate.md`)**:
   - Invariante mandatória determinando que nenhuma funcionalidade é considerada entregue sem cumprir os 5 elos da Cadeia de Potência Máxima.
   - Atualização do Quality Gate para incluir auditoria de auto-conexão (`corporate-engineer audit --wiring`).

2. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `ModuleWiringStatus`: Representação estrita do status de conexão por módulo Python (caminho, se tem exports públicos, lista de símbolos exportados, se possui cobertura de testes unitários dedicada, se está exposto na CLI e flag booleana `is_wired`).
   - `WiringAuditReport`: Relatório consolidado de auditoria de auto-conexão contendo total de módulos, módulos conectados, lista de módulos desconectados, percentual de cobertura (`wiring_rate_pct`) e booleano `is_fully_wired`.

3. **Motor Estático de Auditoria de Auto-Conexão (`src/corporate_engineer/quality/wiring_auditor.py`)**:
   - `CapabilityWiringAuditor`: Varredura AST recursiva de `src/corporate_engineer/`, inspeção do `__all__` dos pacotes de domínio, cruzamento com suítes de teste em `tests/`, verificação de subparsers registrados em `parser.py` e auditoria rigorosa de integridade com bloqueio de código órfão.

4. **Auto-Conexão Ativa dos Módulos do Framework**:
   - Identificados e conectados 9 módulos previamente desconectados:
     - `src/corporate_engineer/orchestrator/__init__.py`: `adversarial` (`AdversarialLoopCoordinator`, `AdversarialRedTeam`, `ArchitectureTranscender`), `hooks_runner` (`generate_pre_invocation_hook_output`).
     - `src/corporate_engineer/quality/__init__.py`: `wiring_auditor` (`CapabilityWiringAuditor`), `storage_cleaner` (`SafeStorageCleaner`), `git_hooks_installer` (`install_git_hooks`), `tool_auto_healer` (`handle_post_tool_use`), `tool_security_guard` (`evaluate_tool_security`).
     - `src/corporate_engineer/system_one/__init__.py`: `dataset` (`SystemOneDatasetGenerator`), `trainer` (`SystemOneTrainer`).
     - `src/corporate_engineer/__init__.py`: `CapabilityWiringAuditor`, `generate_pr_url`, `is_branch_pushed`, `push_branch_to_remote`.

5. **Integração no Quality Gate, CLI e Pipeline Autônomo**:
   - CLI: Adicionada a flag `--wiring` ao subcomando `audit` (`corporate-engineer audit --wiring`).
   - Quality Gate: Método `run_wiring_audit()` adicionado ao `QualityGateRunner`.
   - Pipeline FSM: Acoplamento do `run_wiring_audit()` na fase `AUDIT` do `AutonomousEngineeringGraph.run_pipeline`, falhando formalmente se houver módulos desconectados.

6. **Shift-Left TDD (`tests/test_auto_wiring_integrity.py`)**:
   - 7 novos testes unitários e de integração validando os modelos DTO, auditoria de exports públicos, bloqueio de módulos órfãos, execução via CLI `--wiring`, e gate no pipeline autônomo.
   - Suíte global mantida em **301/301 testes PASS** em 54.72s.

---

## 🧪 Plano de Testes & Validação

- [x] Teste de contratos Pydantic v2 para status e relatório de fiação (`test_module_wiring_status_and_report_models`)
- [x] Teste de varredura AST e auditoria de módulos conectados (`test_capability_wiring_auditor_inspects_codebase`)
- [x] Teste de detecção e bloqueio de módulos órfãos simulados (`test_wiring_auditor_detects_unwired_module`)
- [x] Teste de auditoria do QualityGateRunner (`test_quality_gate_runner_wiring_audit`)
- [x] Teste do subcomando CLI `audit --wiring` (`test_cli_audit_wiring_flag`)
- [x] Teste de execução do gate de fiação no `AutonomousEngineeringGraph.run_pipeline` (`test_autonomous_pipeline_executes_wiring_audit`)
- [x] Teste de integridade de auto-conexão de todos os 9 módulos re-exportados (`test_active_domain_modules_are_fully_wired`)
- [x] Pre-Flight Gate 100% verde:
  - `pytest`: 301/301 PASS em 54.72s
  - `ruff check .`: 0 erros em 166 arquivos
  - `ruff format --check .`: 0 erros de formatação
  - `mypy .`: 0 erros de tipagem estática
  - `secret_scanner.py`: 0 credenciais detectadas
  - `corporate-engineer audit --wiring`: PASS (100% dos módulos conectados)
