# ADR-035: Imutabilidade Estrita em DTOs Pydantic v2 & Curadoria de Skills DAILY vs LIBRARY (Onda P3: IMP-0040 + IMP-0041)

## Status
Aceito (Accepted) — Executando Onda P3 via `SwarmCoordinator` (`RoleExecutor` + Analisadores Determinísticos)

## Data
2026-11-27

## Contexto & Motivação
A Onda P3 encerra o ciclo de dívidas estruturais e higiene de ecossistema identificadas na auditoria técnica do `corporate-engineer`:

1. **Mutabilidade Padrão em DTOs Pydantic v2 (`IMP-0040` — `src/corporate_engineer/models.py`)**:
   - Os modelos de contrato e relatório em `models.py` são mutáveis por padrão, permitindo mutação in-place após construção em pontos como `AutonomousEngineeringGraph` (`orchestrator/graph.py`), `SwarmCoordinator.run_consensus()` (`orchestrator/swarm.py`), `SystemOneRouter.triage_quality_gate()` (`system_one/router.py`) e `LoraSyntaxValidator.validate_sample()` (`lora/validator.py`).
   - Isso viola a invariante de imutabilidade (`common-coding-style.md`) e expõe relatórios e estados a efeitos colaterais silenciosos em execução concorrente.
2. **Excesso de Skills Genéricas Auto-Carregadas (`IMP-0041` — `.agents/skills/` & `skills-registry.md`)**:
   - `.agents/skills/` contém 331 subdiretórios (a grande maioria de stacks não utilizadas pelo repositório, como Perl, Yoruba, Cisco IOS, Laravel, Swift, Godot, Spring Boot), excedendo o orçamento de contexto de descoberta automática e gerando ruído visual na avaliação técnica.

## Decisão de Arquitetura

### 1. Imutabilidade Estrita (`ConfigDict(frozen=True)`) em DTOs de Contrato, Estado e Relatório (`IMP-0040`)
- Aplicar `model_config = ConfigDict(frozen=True)` em **todos os 55 modelos de contrato, estado e relatório** em `src/corporate_engineer/models.py`.
- Preservar mutabilidade controlada apenas nos 2 *handles* vivos de execução concorrente/telemetria (`SwarmMember` — atualizado sob `RLock` em `SwarmCoordinator.dispatch_task()` — e `AgentSpan` — preenchido entre `start_span()` e `end_span()` em `AgentTracer`), mantendo compatibilidade estrita com contratos de concorrência e OpenTelemetry já testados.
- Em `SemanticEvaluationReport.model_post_init()`, utilizar `object.__setattr__(self, ...)` para calcular `composite_score`, `total_violations`, `letter_grade` e `passed_gate` mantendo a instância congelada após inicialização.
- Refatorar consumidores que mutavam DTOs in-place para padrões imutáveis via `model_copy(update=...)`:
  - `AutonomousEngineeringGraph` (`orchestrator/graph.py`): transições FSM em `self.state` (`record_iteration`, `step_plan`, `step_tdd`, `step_implement`, `step_audit`, `run_pipeline`).
  - `SwarmCoordinator.run_consensus()` (`orchestrator/swarm.py`): síntese do `SwarmGoalReport` final via `report.model_copy(update=...)`.
  - `SystemOneRouter.triage_quality_gate()` (`system_one/router.py`): preenchimento de `suggested_agent`, `requires_human_approval` e `risk_level` via `report.model_copy(update=...)`.
  - `LoraSyntaxValidator.validate_sample()` (`lora/validator.py`): remover mutação in-place de `sample.is_valid`/`sample.syntax_errors` e expor avaliação pura (com `validate_sample_model()` retornando cópia atualizada via `model_copy`).

### 2. Curadoria `DAILY` vs `LIBRARY` em `.agents/skills/` (`IMP-0041`)
- Seguindo os critérios do `agent-sort`: *"LIBRARY does not mean delete; it means keep accessible without loading by default"*.
- Manter em `.agents/skills/` **apenas as 21 skills core (`DAILY`)** efetivamente vinculadas ao stack Python, TDD, Segurança, MCP, Arquitetura, Cache AST e Workflows ativos do `corporate-engineer`:
  - 13 `DAILY` canônicas (`corp-pipeline`, `grill-me_v2`, `plan_v2`, `python-patterns`, `python-testing`, `tdd-workflow`, `security-review`, `api-design`, `mcp-server-patterns`, `agentic-engineering`, `conventional-commit-review`, `verification-loop`, `agent-sort`).
  - 8 skills referenciadas diretamente por workflows/código/governança (`security-scan`, `ecc-guide`, `orch-add-feature`, `orch-change-feature`, `orch-fix-defect`, `orch-refine-code`, `architecture-decision-records`, `content-hash-cache-pattern`).
- Mover as demais **310 skills `LIBRARY`** off-stack para `.agents/skills-library/` (fora do escopo de auto-descoberta de `.agents/skills/`).
- Atualizar `.agents/orchestration/skills-registry.md` e `.agents/ecc-install-state.json` refletindo exatamente as 21 skills `DAILY` ativas e o catálogo indexado das 310 skills `LIBRARY` sob demanda.

## Consequências
- **Positivas**: Rejeição em tempo de execução (`ValidationError`) de qualquer mutação indevida em contratos/relatórios/estados Pydantic; eliminação de overflow de contexto de skills no Antigravity; preservação integral dos scripts de `corp-pipeline` (`secret_scanner.py`, `stack_detector.py`, `pr_automator.py`) e zero perda de catálogo offline.
- **Riscos e Mitigações**: Chamadores externos que esperavam mutação direta de `AgentState` ou `SwarmGoalReport` devem usar `model_copy(update=...)`. Todos os testes existentes e novos testes TDD P3 validam o comportamento completo.
