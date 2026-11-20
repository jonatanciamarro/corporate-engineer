# Pull Request: feat: add dynamic mermaid diagram export for dag fsm and checkpoints (IMP-0005)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0005` (Ref: `CORP-003`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/cli.py`
  - `src/corporate_engineer/orchestrator/graph.py`
  - `docs/adr/ADR-003-dag-mermaid-export.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_cli.py`
  - `tests/test_orchestrator.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0005-dag-mermaid-export` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0005`** do backlog contínuo de melhorias (`improvement-backlog.md`), viabilizando a exportação e visualização dinâmica em Mermaid dos estados da máquina FSM e do histórico de checkpoints de execução.

### Principais Entregas:
1. **Serialização Mermaid no Orquestrador (`src/corporate_engineer/orchestrator/graph.py`)**:
   - `AutonomousEngineeringGraph.fsm_to_mermaid(highlight_phase: str | None = None) -> str`: Gera o fluxo topológico da FSM em `flowchart TD` (`PLANNING` ➔ `TDD` ➔ `IMPLEMENT` ➔ `AUDIT` ➔ `DELIVER`) com estilização destacada do nó ativo.
   - `AutonomousEngineeringGraph.to_mermaid(highlight_current: bool = False) -> str`: Método de conveniência que injeta o estado atual da instância do grafo.
   - `AutonomousEngineeringGraph.checkpoints_to_mermaid(checkpoints: list[dict[str, Any]]) -> str`: Constrói dinamicamente uma timeline cronológica (`flowchart LR`) com nós detalhando cada checkpoint persistido (`ticket_id`, `filename`, `phase`, `iteration_count`).

2. **Novas Flags na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - `corporate-engineer dag --mermaid`: Imprime o diagrama Mermaid da topologia FSM no stdout.
   - `corporate-engineer dag --checkpoints --mermaid`: Imprime o diagrama Mermaid cronológico dos checkpoints do workspace.
   - `corporate-engineer dag --mermaid --output <path>`: Salva a representação diretamente em arquivo de destino (`.mmd`, `.md`, etc.).

3. **Arquitetura Formal (ADR-003)**:
   - Registro de decisão formal documentado em `docs/adr/ADR-003-dag-mermaid-export.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: 7 novos testes unitários e de CLI falharam comprovadamente antes da implementação (`AttributeError` e `unrecognized arguments`).
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação cirúrgica.
- [x] **Expansão da Suíte**: De 62 para **69 testes passando** em 2.78s.
- [x] **Cobertura Global**: **92%** de cobertura de código (`pytest-cov`).

### Testes Adicionados:
- `tests/test_orchestrator.py::test_graph_fsm_to_mermaid`
- `tests/test_orchestrator.py::test_graph_instance_to_mermaid_with_highlight`
- `tests/test_orchestrator.py::test_graph_checkpoints_to_mermaid`
- `tests/test_orchestrator.py::test_graph_checkpoints_to_mermaid_empty`
- `tests/test_cli.py::test_cli_dag_mermaid`
- `tests/test_cli.py::test_cli_dag_mermaid_output_file`
- `tests/test_cli.py::test_cli_dag_checkpoints_mermaid`

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 69/69 PASS (`pytest`)
- [x] **Code Linter**: 0 violações (`ruff check .`)
- [x] **Code Formatter**: 36 arquivos verificados e formatados (`ruff format --check .`)
- [x] **Static Type Checker**: 0 erros em 22 arquivos (`mypy .`)
- [x] **Secret Scanner**: 0 credenciais ou tokens expostos (`secret_scanner.py`)
