# ADR-019: Autonomous End-to-End Engineering Runner & Dogfooding Pipeline

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
O framework `corporate-engineer` desenvolveu diversos componentes de engenharia de ponta:
- A máquina de estados finitos determinística (`AutonomousEngineeringGraph`);
- O motor de refinamento contextual de metaprompt ancorado em AST (`ContextAwarePromptRefiner`);
- O motor de auto-cura e remediação estrutural de código (`ASTSelfHealingFixer`);
- O executor de portões de qualidade e segurança (`QualityGateRunner`);
- A instrumentação de telemetria compatível com OpenTelemetry (`AgentTracer`).

Contudo, o ponto de entrada principal para usuários e agentes, o subcomando de CLI `corporate-engineer run`, apenas inicializava a estrutura do grafo e emitia mensagens preliminares na console, sem conduzir o fluxo de trabalho através de suas 5 fases obrigatórias (`PLANNING` -> `TDD` -> `IMPLEMENT` -> `AUDIT` -> `DELIVER`), sem persistir checkpoints determinísticos em disco e sem consolidar um relatório executivo de entrega.

A iniciativa **IMP-0019** (Trilha Estratégica 3 do Roadmap) foi implementada para materializar o ciclo completo de execução autônoma end-to-end e permitir o *dogfooding* prático do framework em projetos e demandas reais.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `RunExecutionReport`: Contrato fortemente tipado para reporte de execuções completas, contendo `ticket_id`, `task_description`, `status` (`SUCCESS`, `AUDIT_FAILED`, `FAILED`, `BUDGET_EXCEEDED`, `PENDING_APPROVAL`), `final_phase`, `iterations`, `checkpoints_created`, `refined_plan`, `test_files`, `code_changes_count`, `audit_passed`, `duration_seconds`, `trace_id`, `dry_run` e `details`.

2. **Motor de Ciclo Completo (`src/corporate_engineer/orchestrator/graph.py`)**:
   - Adição do método `run_pipeline(dry_run=False, auto_deliver=True, strict_audit=True) -> RunExecutionReport`:
     - **Fase 1 (PLANNING)**: Executa `ContextAwarePromptRefiner` sobre a descrição da tarefa, identifica domínios, âncoras AST e guardrails de escopo, atualiza o plano e persiste checkpoint `cp_<TICKET>_PLANNING_<N>.json`.
     - **Fase 2 (TDD)**: Extrai cenários de teste da especificação refinada, avança o grafo para TDD e persiste checkpoint.
     - **Fase 3 (IMPLEMENT)**: Mapeia módulos afetados, registra diffs ou auto-remediações cirúrgicas, avança para IMPLEMENT e persiste checkpoint.
     - **Fase 4 (AUDIT)**: Executa `QualityGateRunner` no workspace (scanner de segredos e testes estritos opcionais). Se aprovado, transiciona para `DELIVER`; se reprovado, retém na fase e reporta status `AUDIT_FAILED`.
     - **Fase 5 (DELIVER)**: Finaliza medição de tempo, registra telemetria OpenTelemetry e retorna o `RunExecutionReport`.

3. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer run` ampliado com as flags:
     - `--dry-run`: Execução em modo de simulação segura, garantindo dogfooding não-destrutivo;
     - `--strict-audit`: Exigência de execução completa da suíte de testes no portão de auditoria;
     - `--format [text|json|markdown]`: Suporte a múltiplos formatos de visualização e automação;
     - `--output`: Exportação direta do relatório para arquivo.

4. **Higiene de Workspace (`.gitignore`)**:
   - Inclusão de `.checkpoints/` no `.gitignore` para assegurar que snapshots gerados durante execuções locais ou testes não poluam o histórico do Git.

## Consequências

- **Positivas**:
  - Capacidade real de dogfooding e execução autônoma end-to-end com um único comando da CLI.
  - Rastreabilidade integral com checkpoints JSON cronológicos a cada transição de fase.
  - Prevenção ativa de regressões: qualquer falha no portão de auditoria interrompe o avanço para a fase de entrega.
  - Saída flexível em texto formatado, JSON estruturado ou Markdown para relatórios executivos e PRs.
- **Mitigações**:
  - O modo `--dry-run` permite rodar validações completas sem risco de mutação indevida no repositório.
  - Isolamento de caminhos e tolerância a tipos (`Path` e `str`) em todos os runners corporativos.
