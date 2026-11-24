# ADR-026: Modularização e Decomposição da CLI Corporativa (IMP-0023)

## Status
Aceito (Accepted)

## Data
2026-11-24

## Contexto & Motivação
O framework `corporate-engineer` expandiu seu ecossistema através de 25 melhorias de alta sofisticação. Como ponto de entrada unificado para desenvolvedores humanos e agentes autônomos, o arquivo `src/corporate_engineer/cli.py` acumulou 19 subcomandos de topo (`run`, `index`, `audit`, `dag`, `mcp`, `pr`, `eval`, `blast-radius`, `telemetry`, `test-surgical`, `decide`, `dataset`, `fix`, `clean`, `benchmark`, `swarm`, `prompt`, `lora`, `anticipate`) com diversos subcomandos aninhados, atingindo **1.701 linhas de código**.

Esta concentração em um único monólito apresenta problemas severos:
1. **Violação das Invariantes de Engenharia**: O framework estipula um limite suave de 800 linhas para arquivos de código-fonte (sendo 200-400 linhas o intervalo ideal de coesão).
2. **Alto Acoplamento e Dificuldade de Revisão**: Qualquer alteração em um subcomando concorria com edições em outros módulos, elevando o risco de merge conflicts.
3. **Imports Tardios Desnecessários**: Para evitar custo de importação de toda a biblioteca no bootstrap, dezenas de imports locais foram inseridos dentro de cada função `handle_*`.
4. **Dificuldade de Extensibilidade**: Adicionar uma nova capacidade exigia editar um arquivo de quase 2.000 linhas.

## Decisão de Arquitetura

Decidiu-se decompor o monólito `src/corporate_engineer/cli.py` em um subpacote modular com separação estrita por domínios de negócio:

### 1. Estrutura do Subpacote `src/corporate_engineer/cli/`

```
src/corporate_engineer/cli/
├── __init__.py           # Fachada pública re-exportando main, build_parser e handle_* (100% retrocompatível)
├── __main__.py           # Suporte a execução via `python -m corporate_engineer.cli`
├── main.py               # Dispatcher e lógica de execução principal (<100 linhas)
├── parser.py             # Montagem do ArgumentParser central e orquestração de subparsers (<150 linhas)
└── commands/             # Comandos encapsulados por domínio funcional
    ├── __init__.py
    ├── orchestrator.py   # Subcomandos: `run`, `dag`, `swarm`, `anticipate`
    ├── rag.py            # Subcomandos: `index`, `blast-radius`, `eval`
    ├── quality.py        # Subcomandos: `audit`, `test-surgical`, `fix`, `clean`
    ├── system_one.py     # Subcomandos: `decide`, `dataset`, `benchmark`
    ├── mcp.py            # Subcomando: `mcp` (ping, list-tools, call, hub)
    ├── prompt.py         # Subcomando: `prompt` (refine)
    ├── telemetry.py      # Subcomando: `telemetry`
    ├── pr.py             # Subcomando: `pr`
    └── lora.py           # Subcomando: `lora` (generate, validate, export)
```

### 2. Padrão de Encapsulamento por Módulo
Cada módulo em `commands/` expõe:
- Funções de registro de argumentos: `register_<subcommand>_parser(subparsers: argparse._SubParsersAction) -> None`
- Funções de execução: `handle_<subcommand>(args: argparse.Namespace) -> int`

### 3. Garantia de Retrocompatibilidade Total
- O ponto de entrada oficial `corporate-engineer = "corporate_engineer.cli:main"` em `pyproject.toml` continua intacto.
- A invocação via CLI `python -m corporate_engineer.cli <subcomando>` é mantida via `__main__.py`.
- Importações existentes nos testes (`from corporate_engineer.cli import main`, `from corporate_engineer.cli import handle_prompt`) continuam funcionando de forma transparente através das re-exportações em `src/corporate_engineer/cli/__init__.py`.

## Consequências

- **Manutenibilidade Elevada**: O arquivo principal `main.py` e o orquestrador `parser.py` possuem <150 linhas cada; nenhum módulo de comando ultrapassa 350 linhas.
- **Isolamento de Falhas**: Modificações em um comando (ex: `lora` ou `swarm`) não impactam os demais módulos nem geram conflitos no Git.
- **Zero Regressão**: 100% dos testes CLI existentes continuam verdes sem necessidade de alteração de assinaturas ou comportamento.
