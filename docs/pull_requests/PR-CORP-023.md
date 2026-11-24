# PR: refactor(cli): modularize monolithic cli into domain command packages (IMP-0023 / ADR-026)

## 📌 Resumo das Modificações
Decomposição completa do monólito de 1.884 linhas (`src/corporate_engineer/cli.py`) em um subpacote altamente modular e coeso (`src/corporate_engineer/cli/`), em estrita conformidade com o **ADR-026**, preservando 100% de compatibilidade retroativa:

1. **Subpacote Modular de Comandos (`src/corporate_engineer/cli/commands/`)**:
   - `orchestrator.py`: `run`, `dag`, `swarm`, `anticipate`, mais constantes FSM `DAG_PHASES` e `DAG_TRANSITIONS`.
   - `rag.py`: `index`, `blast-radius`, `eval`, e helper `_run_blast_radius_analysis`.
   - `quality.py`: `audit`, `test-surgical`, `fix`, `clean`.
   - `system_one.py`: `decide`, `dataset`, `benchmark`.
   - `mcp.py`: `mcp` (`ping`, `list-tools`, `call`, `hub`).
   - `prompt.py`: `prompt` (`refine`).
   - `telemetry.py`: `telemetry` e `_print_trace_report`.
   - `pr.py`: `pr-link` (`handle_pr_link`).
   - `lora.py`: `lora` (`generate`, `validate`, `export`).
   - `commands/__init__.py`: re-exporta e agrupa todos os 9 módulos de comandos.

2. **Módulos Centrais da CLI**:
   - `src/corporate_engineer/cli/parser.py`: Centraliza `build_parser() -> argparse.ArgumentParser` delegando registro a cada `register_*_parser`.
   - `src/corporate_engineer/cli/main.py`: Centraliza `main(argv) -> int` com tabela determinística de despacho `_DISPATCH_MAP`.
   - `src/corporate_engineer/cli/__main__.py`: Suporte nativo a execução via `python -m corporate_engineer.cli`.
   - `src/corporate_engineer/cli/__init__.py`: Re-exporta `main`, `build_parser` e todas as 19 funções `handle_*` mantendo a interface pública idêntica.

3. **Invariante de Tamanho de Arquivo**:
   - Todos os arquivos do subpacote `src/corporate_engineer/cli/` possuem estritamente menos de 800 linhas (maior arquivo com 421 linhas, maioria < 250 linhas).

4. **Shift-Left TDD (`tests/test_cli_modular_architecture.py`)**:
   - Suíte de 3 testes validando exportações públicas, importabilidade e contratos de todos os módulos de comando e teto estrito de 800 linhas.
   - Suíte global expandida para **287/287 testes PASS**.

---

## 🧪 Plano de Testes & Validação

- [x] Teste de exportações públicas do pacote (`test_cli_package_public_exports`)
- [x] Teste de importabilidade dos 9 módulos de comando (`test_cli_command_modules_importable`)
- [x] Teste estrito de teto de 800 linhas por arquivo (`test_cli_file_size_limits`)
- [x] Suíte existente de testes de CLI (`tests/test_cli.py`: 23/23 PASS)
- [x] Execução direta via módulo Python (`python -m corporate_engineer.cli --help`: todos os 19 subcomandos funcionais)
- [x] Pre-Flight Gate 100% verde:
  - `pytest`: 287/287 PASS em 42.17s
  - `ruff check .`: 0 erros
  - `ruff format --check .`: 159 arquivos formatados
  - `mypy .`: 0 erros em 97 arquivos
  - `secret_scanner.py`: 0 credenciais detectadas
