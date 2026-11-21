# ADR-012: AST Auto-Refactor & Self-Healing Fixer (Auto-Remediação de Código)

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
No framework `corporate-engineer`, as ferramentas de auditoria estática (`corporate-engineer audit`) e scorecard semântico (`corporate-engineer eval`) são capazes de diagnosticar com alta precisão inconformidades estruturais no código-fonte, tais como:
1. Métodos `__init__` sem anotação explícita de retorno (`-> None`), violando o padrão estrito de tipagem corporativa (Mypy/PEP 484);
2. Argumentos padrão mutáveis em funções (ex.: `def func(items=[])` ou `def func(data={})`), introduzindo estado compartilhado perigoso e bugs sutis;
3. Instruções redundantes como declarações `pass` desnecessárias em blocos que já contêm docstrings ou retornos;
4. Variáveis ou definições de funções sem documentação ou contratos estruturais mínimos.

Até o momento, a resolução dessas violações dependia de intervenção manual do desenvolvedor ou de chamadas dispendiosas ao LLM do Sistema 2. Isso gerava atrito, atrasava o ciclo de entrega e aumentava o custo de tokens para refatorações puramente mecânicas e determinísticas.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `FixDetail`: Registra os detalhes de cada correção aplicada cirurgicamente (`file_path`, `rule_name`, `line_number`, `description`, `original_snippet`, `fixed_snippet`).
   - `FixReport`: Relatório consolidado de auto-remediação contendo `total_files_analyzed`, `files_modified`, `fixes_applied: list[FixDetail]`, `dry_run: bool`, `system_one_risk: str` e `success: bool`.

2. **Motor AST NodeTransformer (`src/corporate_engineer/eval/fixer.py`)**:
   - Classe `ASTSelfHealingFixer`: Utiliza a biblioteca padrão `ast` do Python (`ast.NodeTransformer` e `ast.unparse`) para aplicar transformações estritamente seguras e conservadoras no código:
     - `InitReturnAnnotationFixer`: Adiciona automaticamente `-> None` a métodos `__init__` que não possuem tipagem de retorno.
     - `MutableDefaultArgumentFixer`: Converte argumentos padrão mutáveis (listas vazias `[]`, dicionários vazios `{}`) para `None` e injeta a inicialização segura `if param is None: param = []` no início do corpo da função.
     - `RedundantPassCleaner`: Remove declarações `pass` supérfluas em classes ou funções que já contêm docstrings ou outras instruções.
   - **Modo Dry-Run Determinístico**: Suporte a `--dry-run` para geração de relatórios de impacto e diffs unificados antes da escrita em disco.
   - **Guardrail de Risco via Sistema 1**: Integração com o `SystemOneRouter` para classificar o nível de risco da alteração antes da persistência, garantindo que transformações não afetem contratos públicos de API.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer fix`:
     - `--auto`: Aplica as correções automáticas e salva nos arquivos.
     - `--dry-run`: Executa as transformações em memória e exibe o relatório de correções sem alterar o disco.
     - `--path <path>`: Alvo das correções (arquivo específico ou diretório).
     - `--format [text|json]`: Suporte a saída legível para humanos ou JSON para pipelines CI/CD.

## Consequências
- **Positivas**:
  - Auto-remediação instantânea (<100ms) e determinística de violações comuns de código.
  - Redução drástica da necessidade de invocar LLMs para correções mecânicas.
  - Aumento autônomo na pontuação do scorecard semântico (`corporate-engineer eval`).
  - Segurança matemática preservada através de `ast.parse` e validação sintática pós-transformação.
- **Mitigações**:
  - Toda transformação é revalidada via `ast.parse()` antes de ser gravada, garantindo que nenhuma sintaxe inválida seja produzida.
  - O modo `--dry-run` permite inspeção prévia de todos os diffs.
