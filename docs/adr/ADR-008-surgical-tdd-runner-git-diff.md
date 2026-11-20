# ADR-008: Surgical TDD Runner Integrado ao Git Diff & Blast Radius

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
Em repositórios corporativos de grande porte e com dezenas ou centenas de suítes de teste, a execução integral da suíte a cada micro-iteração de código cria um gargalo substancial no ciclo de desenvolvimento guiado por testes (Shift-Left TDD):
1. O desenvolvedor ou agente autônomo perde tempo esperando a suíte inteira rodar quando alterou apenas um método ou módulo pontual.
2. A análise manual de impacto (ou inspeção prévia de `blast-radius`) exige múltiplos passos manuais: calcular o raio de explosão, inspecionar a saída textual, copiar a lista de testes afetados e montar manualmente o comando `pytest`.
3. Para fluxos de CI/CD pré-commit ou pre-flight em branches locais, é crítico ter um executor cirúrgico que inspecione automaticamente o `git diff` contra a branch base (ex.: `main`) e o estado não commitado da working tree, executando instantaneamente apenas os testes que realmente cobrem os arquivos ou símbolos modificados.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `SurgicalTestReport`: Contrato fortemente tipado para o resultado da execução cirúrgica (`base_branch`, `changed_files`, `affected_tests`, `command`, `executed`, `exit_code`, `stdout`, `stderr`, `duration_ms`, `passed`).

2. **Módulo de Execução Cirúrgica (`src/corporate_engineer/quality/surgical_runner.py`)**:
   - `SurgicalTestRunner`: Orquestrador que integra a camada de versionamento (Git) e a camada de inteligência de código (`BlastRadiusAnalyzer`).
   - `get_changed_files(base_branch, include_uncommitted)`: Detecta arquivos modificados, adicionados, renomeados ou não commitados no working tree e no diff da branch ativa.
   - `resolve_affected_tests(changed_files, max_depth)`: Mapeia diretamente arquivos de teste alterados e utiliza análise de grafo AST para determinar testes transitivamente impactados por alterações no código fonte.
   - `build_command(affected_tests, extra_args)`: Resolve deterministicamente o executável pytest apropriado (`.venv` Scripts/bin ou `sys.executable -m pytest`) e monta os argumentos.
   - `run(...)`: Executa cirurgicamente apenas os testes afetados, medindo tempo com precisão monotônica e retornando o relatório estruturado.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adicionado subcomando de primeira classe `corporate-engineer test-surgical`:
     - Flags: `--base-branch`, `--depth`, `--dry-run`, `--fallback-all`, `--workspace`, `--format text|json`, `--output` e argumentos adicionais para o pytest via `pytest_extra_args`.

## Consequências
- **Positivas**:
  - Redução drástica (até 80-90%) no tempo de feedback do loop TDD e verificação pré-commit.
  - Zero atrito para o desenvolvedor e agentes: `test-surgical` cuida da descoberta, cálculo de impacto e execução.
  - Modo `--dry-run` permite inspecionar quais testes serão acionados antes de rodar.
  - Suporte a saída estruturada em JSON para automação em pipelines de CI e IDEs.
- **Limitações Mitigadas**:
  - Opção `--fallback-all` garante que se arquivos sem mapeamento direto de teste forem alterados, a suíte completa possa ser executada por segurança.
