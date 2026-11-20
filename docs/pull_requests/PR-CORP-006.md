# Pull Request: feat: add code graphrag blast radius and impact analysis engine (IMP-0008)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0008` (Ref: `CORP-006`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/rag/impact.py`
  - `src/corporate_engineer/rag/__init__.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-006-code-graphrag-blast-radius-impact.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_impact.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0008-blast-radius-impact` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0008`** do backlog contínuo de melhorias (`improvement-backlog.md`), introduzindo o motor de **Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças** no framework `corporate-engineer`.

A funcionalidade permite determinar com precisão o raio de explosão de qualquer alteração de código (em nível de símbolo ou de arquivo), computando chamadores diretos, dependentes transitivos e recomendando a execução cirúrgica apenas dos testes afetados pela mudança.

### Principais Entregas:
1. **Motor de Análise de Impacto (`src/corporate_engineer/rag/impact.py`)**:
   - Classe `BlastRadiusAnalyzer` que inspeciona a AST da base de código e constrói grafos de dependência reversa de chamadas e importações.
   - Algoritmo BFS para cálculo de propagação de impacto com controle de profundidade máxima (`max_depth`).
   - Resolução inteligente de suítes de teste afetadas (`tests/test_*.py`), filtrando apenas os testes relacionados aos símbolos ou arquivos impactados.

2. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `ImpactNode`: Representa nós no grafo de impacto (`symbol`, `file_path`, `depth`, `impact_type`: `DIRECT` | `TRANSITIVE`, `relationship`: `CALLS` | `IMPORTS`).
   - `BlastRadiusReport`: Contrato consolidado agregando contagem de arquivos e símbolos afetados, árvore de propagação, lista de testes afetados e o comando cirúrgico recomendado (`recommended_test_command`).

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando dedicado `corporate-engineer blast-radius <target> [--depth N] [--workspace .] [--format text|json]`.
   - Adicionada flag `--impact-of <target>` e `--depth N` ao subcomando existente `corporate-engineer index`.
   - Visualização textual em árvore categorizada por profundidade (`DIRECT IMPACT` e `TRANSITIVE IMPACT`) e formato JSON estruturado.

4. **Arquitetura Formal (ADR-006)**:
   - Formalizada em `docs/adr/ADR-006-code-graphrag-blast-radius-impact.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_impact.py` falharam antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 84 para **88 testes passando** em 6.13s.
- [x] **Cobertura Global**: **90%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 88/88 PASS (`pytest`)
- [x] **Code Linter**: 0 violações (`ruff check .`)
- [x] **Code Formatter**: 51 arquivos verificados e formatados (`ruff format --check .`)
- [x] **Static Type Checker**: 0 erros em 31 arquivos (`mypy .`)
- [x] **Secret Scanner**: 0 credenciais ou tokens expostos (`secret_scanner.py`)
