# Pull Request: feat: add native ast mutation testing engine for test quality evaluation (IMP-0006)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0006` (Ref: `CORP-004`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/quality/mutation.py`
  - `src/corporate_engineer/quality/gate.py`
  - `src/corporate_engineer/quality/__init__.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-004-ast-mutation-testing-engine.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_mutation.py`
  - `tests/test_cli.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0006-mutation-testing-engine` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0006`** do backlog contínuo de melhorias (`improvement-backlog.md`), introduzindo um **Motor Nativo de Mutation Testing via AST** para validar a assertividade e a resiliência real de suítes de testes geradas por IA contra mutações lógicas.

Além disso, foram formalizadas e registradas no backlog contínuo as propostas:
- `IMP-0007`: Evaluation-Driven Development (EDD) & Scorecard Semântico.
- `IMP-0008`: Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças.

### Principais Entregas:
1. **Motor de Mutação AST (`src/corporate_engineer/quality/mutation.py`)**:
   - `scan_mutation_points(source_code)`: Detecta operadores relacionais (`==`, `!=`, `<`, `<=`, `>`, `>=`), binários aritméticos (`+`, `-`, `*`, `//`) e booleanos literais (`True`, `False`).
   - `apply_mutation(source_code, point)`: Transforma a AST e descompila código mutado via `ast.unparse`.
   - `ASTMutationEngine`: Orquestra a execução da suíte de testes contra cada mutante em subprocesso isolado, calculando o `MutationScore`.
   - Garantia de preservação e restauração do código original via bloco `finally`.

2. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `Mutant`: Representa cada mutante com `id`, `file_path`, `line_number`, `original_op`, `mutated_op`, `status` (`KILLED` | `SURVIVED` | `ERROR`).
   - `MutationReport`: Agrega estatísticas completas com `total_mutants`, `killed`, `survived`, `errors`, `mutation_score` e lista de mutantes.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - `corporate-engineer audit --mutation`: Executa teste de mutação no projeto.
   - `corporate-engineer audit --mutation --target-file <path> --max-mutants <N>`: Permite análise cirúrgica e parametrizada.

4. **Arquitetura Formal (ADR-004)**:
   - Registro formal documentado em `docs/adr/ADR-004-ast-mutation-testing-engine.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Novos testes em `tests/test_mutation.py` falharam antes da implementação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a codificação.
- [x] **Expansão da Suíte**: De 69 para **74 testes passando** em 4.92s.
- [x] **Cobertura Global**: **91%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 74/74 PASS (`pytest`)
- [x] **Code Linter**: 0 violações (`ruff check .`)
- [x] **Code Formatter**: 39 arquivos verificados e formatados (`ruff format --check .`)
- [x] **Static Type Checker**: 0 erros em 24 arquivos (`mypy .`)
- [x] **Secret Scanner**: 0 credenciais ou tokens expostos (`secret_scanner.py`)
