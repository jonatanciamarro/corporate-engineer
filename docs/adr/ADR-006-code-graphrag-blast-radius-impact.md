# ADR-006: Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
Em bases de código mantidas por equipes de engenharia corporativa e agentes de IA autônomos, alterações em funções centrais, modelos de dados ou utilitários podem gerar impactos colaterais inesperados em múltiplos módulos dependentes.

O indexador AST existente (`ASTCodebaseIndexer` e `CachedASTIndexer`) constrói grafos direcionados de chamada ("função A chama função B") e mapeamento de importações ("arquivo A importa arquivo B"). No entanto, ele não computava a **análise reversa de impacto** (Blast Radius): responder instantaneamente à pergunta *"Se o arquivo X ou a função Y for alterada, quais componentes e testes são direta e transitivamente afetados?"*.

Conforme preconizado pelo relatório *Deep Research AI Software Engineering 2026*, pipelines eficientes de agentes utilizam **Blast Radius Analysis** para restringir a execução de testes apenas aos componentes impactados, reduzindo o tempo de ciclo TDD e o consumo de tokens/recursos de computação.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `ImpactNode`: Representa um nó afetado na árvore de dependências reversas, contendo `symbol`, `file_path`, `depth`, `impact_type` (`DIRECT` ou `TRANSITIVE`) e `relationship` (`CALLS`, `IMPORTS`, `INHERITS`).
   - `BlastRadiusReport`: Contrato consolidado contendo `target`, `target_type`, `total_impacted_files`, `total_impacted_symbols`, `impacted_nodes`, `affected_tests` e `recommended_test_command`.

2. **Motor de Análise de Blast Radius (`src/corporate_engineer/rag/impact.py`)**:
   - Classe `BlastRadiusAnalyzer` que consome as estruturas geradas pelo `ASTCodebaseIndexer`.
   - Constrói o grafo de dependências reversas (grafo bipartido de arquivos e símbolos).
   - Realiza busca em largura (BFS) a partir do nó alvo até a profundidade configurada (`max_depth`, padrão 3).
   - Cruza nós afetados com a suíte de testes (mapeando arquivos `tests/test_*.py` que importam ou testam os símbolos afetados).

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Suporte via flag `--impact-of <target>` no subcomando `index` e subcomando dedicado `blast-radius`:
     ```bash
     corporate-engineer index --impact-of git_utils.py --depth 2
     corporate-engineer blast-radius generate_pr_url --depth 3 --format json
     ```
   - Emite saída visual em árvore no formato `text` e estrutura completa serializada no formato `json`.

## Consequências
- **Positivas**:
  - Isolamento preciso do raio de explosão de qualquer mudança na base de código.
  - Execução cirúrgica de testes, acelerando loops de TDD e reduzindo custos em CI.
  - Alinhamento pleno com a arquitetura GraphRAG de navegação semântica de código.
- **Limitações Mitigadas**:
  - Chamadas dinâmicas reflexivas (ex.: `getattr`) continuam cobertas no nível de importação de arquivos via grafo de imports estático.
