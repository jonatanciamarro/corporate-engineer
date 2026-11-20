# ADR-005: Evaluation-Driven Development (EDD) & Scorecard Semântico

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
Em fluxos modernos de engenharia com agentes de IA autônomos (Enterprise AI Agentic Engineering), ferramentas de linter como Ruff e verificadores estáticos como Mypy cobrem regras sintáticas e verificação de tipos. No entanto, elas não avaliam a **aderência semântica e arquitetural** aos padrões corporativos definidos (ex.: imutabilidade de objetos, uso de contratos Pydantic v2 ao invés de dicionários dinâmicos, complexidade ciclomática e higiene de modularidade).

Conforme documentado no relatório *Deep Research AI Software Engineering 2026*, sistemas autônomos de engenharia necessitam de **Evaluation-Driven Development (EDD)**: um scorecard semântico automatizado e mensurável que forneça notas objetivas de 0 a 100 em eixos padronizados de qualidade antes de qualquer promoção para branches principais.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `EvaluationAxisScore`: Representa o resultado de um eixo individual (`axis_name`, `score` de 0 a 100, `weight`, `violations`, `passed`).
   - `SemanticEvaluationReport`: Agrega todos os eixos, calculando `composite_score`, `letter_grade` (A, B, C, F), `total_files_evaluated`, `violations_count` e `passed_gate`.

2. **Módulo de Avaliação Semântica (`src/corporate_engineer/eval/`)**:
   - `SemanticCodeEvaluator`: Analisador baseado em AST que percorre os arquivos `.py` e calcula pontuações para os 5 eixos corporativos:
     1. **Immutability & Pure Functions (20%)**: Penaliza mutações in-place diretas e variáveis globais.
     2. **Strong Typing & Pydantic Contracts (25%)**: Avalia ratio de contratos DTO/Pydantic em interfaces vs dicionários soltos (`dict` sem tipo ou `Any`).
     3. **Cyclomatic Complexity (20%)**: Analisa ramificações (`if`, `for`, `while`, `except`, `with`, operadores booleanos) e penaliza funções com complexidade ciclomática excessiva (> 8).
     4. **Modularity & Hygiene (15%)**: Valida comprimento de funções (< 50 linhas), número de argumentos (<= 5) e tamanho de arquivos (< 800 linhas).
     5. **Type Annotations Coverage (20%)**: Mede o percentual de funções e parâmetros estritamente anotados com tipos.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adição do subcomando `eval`:
     ```bash
     corporate-engineer eval [path] [--min-score 80.0] [--strict] [--format text|json]
     ```
   - No formato `text`, exibe scorecard tabular com barras visuais e resumo por eixo.
   - No formato `json`, emite o DTO estruturado completo serializado.
   - Retorna código `0` em caso de aprovação no gate ou `1` se o score for menor que `--min-score` ou se houver violações no modo `--strict`.

## Consequências
- **Positivas**:
  - Observabilidade objetiva da conformidade da base de código com os padrões corporativos.
  - Prevenção automática de "AI code bloat" e degeneração de design em pipelines autônomos.
  - Facilidade de integração em pipelines de CI/CD e pre-flight gates.
- **Limitações Mitigadas**:
  - Análise executada diretamente sobre a AST padrão do Python (`ast.parse`), sem dependências pesadas externas e com execução em milissegundos.
