# PR: feat(models,orchestrator,skills): Onda P3 — Imutabilidade Estrita em DTOs Pydantic v2 e Curadoria de Skills DAILY vs LIBRARY (IMP-0040 / IMP-0041 / ADR-035)

## 📌 Resumo das Modificações
Implementação da **Onda P3** orquestrada via `SwarmCoordinator` (`RoleExecutor` + analisadores determinísticos reais) em conformidade com o **ADR-035**:

1. **Imutabilidade Estrita (`ConfigDict(frozen=True)`) nos DTOs Pydantic v2 (`IMP-0040`)**:
   - `src/corporate_engineer/models.py`: introdução da base `_FrozenDTO(BaseModel)` com `model_config = ConfigDict(frozen=True)` aplicada a **55 modelos** de contrato, estado e relatório; preservação intencional e documentada apenas dos 2 *handles* vivos de execução (`SwarmMember` e `AgentSpan`); adaptação de `SemanticEvaluationReport.model_post_init()` via `object.__setattr__`.
   - `src/corporate_engineer/orchestrator/graph.py`: refatoração de `record_iteration`, `step_plan`, `step_tdd`, `step_implement`, `step_audit` e `run_pipeline` para `self.state.model_copy(update=...)`.
   - `src/corporate_engineer/orchestrator/swarm.py`: atualização de `SwarmCoordinator.run_consensus()` para retornar `report.model_copy(update=...)`.
   - `src/corporate_engineer/system_one/router.py`: atualização de `triage_quality_gate()` para `report.model_copy(update=...)`.
   - `src/corporate_engineer/lora/validator.py`: remoção da mutação in-place em `validate_sample()` e criação de `validate_sample_model()` com retorno de cópia imutável.

2. **Curadoria `DAILY` vs `LIBRARY` em `.agents/skills/` (`IMP-0041`)**:
   - Manutenção em `.agents/skills/` de exatamente **21 skills `DAILY`** vinculadas ao stack Python 3.11 / Pydantic v2 / TDD / Segurança / MCP / AST / Corp-Pipeline (preservando os scripts em `.agents/skills/corp-pipeline/scripts/`).
   - Realocação das **310 skills `LIBRARY`** off-stack para `.agents/skills-library/` (sem perda de catálogo).
   - Atualização de `.agents/orchestration/skills-registry.md`, `.agents/ecc-install-state.json`, `.agents/orchestration/improvement-backlog.md` (`IMP-0040` e `IMP-0041` -> `IMPLEMENTED`) e `state.md`.

---

## 🧪 Plano de Testes & Validação

- [x] Shift-Left TDD (`tests/test_p3_immutability_and_skills_curation.py`: 6 novos testes RED → GREEN).
- [x] Pre-Flight Gate completo:
  - `pytest -q`: **409 passed in 127.40s**
  - `ruff check .`: `All checks passed!` (0 erros)
  - `ruff format --check .`: `182 files already formatted`
  - `mypy .`: `Success: no issues found in 105 source files`
  - `secret_scanner.py .`: `PASS` (`0` segredos)
  - `python -m corporate_engineer.cli audit --wiring`: `PASS` (`48/48` módulos conectados)
- [x] Consenso Determinístico do `SwarmCoordinator` (`execution_mode=deterministic-analyzer`): **APPROVED** (`code-reviewer`: `92.34/100 Grade A`, `architect`: `48/48 wired`, `security-reviewer`: `0 secrets`, `rag-pipeline-reviewer`: `577 símbolos AST`).
