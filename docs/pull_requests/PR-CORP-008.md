# Pull Request: feat: add surgical tdd runner integrated with git diff and blast radius (IMP-0010)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0010` (Ref: `CORP-008`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/quality/surgical_runner.py`
  - `src/corporate_engineer/quality/__init__.py`
  - `src/corporate_engineer/rag/impact.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-008-surgical-tdd-runner-git-diff.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_surgical_runner.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0010-surgical-tdd-runner` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0010`** do backlog contínuo de melhorias (`improvement-backlog.md`), introduzindo o **Surgical TDD Runner Integrado ao Git Diff & Blast Radius** no framework `corporate-engineer`.

O recurso conecta de forma automatizada o versionamento de código (Git) e o motor de análise semântica de impacto (Blast Radius AST), permitindo identificar arquivos alterados na branch ou working tree e executar cirurgicamente apenas as suítes de teste afetadas pela mudança, reduzindo radicalmente o tempo do ciclo Shift-Left TDD.

### Principais Entregas:
1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `SurgicalTestReport`: Contrato fortemente tipado para a execução cirúrgica (`base_branch`, `changed_files`, `affected_tests`, `command`, `executed`, `exit_code`, `stdout`, `stderr`, `duration_ms`, `passed`).

2. **Motor Surgical TDD Runner (`src/corporate_engineer/quality/surgical_runner.py`)**:
   - Classe `SurgicalTestRunner` integrando `BlastRadiusAnalyzer` e detecção Git via `git diff` e `git status --porcelain`.
   - Mapeamento inteligente de testes diretos e testes transitivamente dependentes via AST.
   - Resolução cross-platform do binário pytest (`.venv` Scripts/bin ou fallback para `sys.executable -m pytest`).
   - Suporte a modo `--dry-run` e opção de fallback seguro (`--fallback-all`).

3. **Melhorias no Analisador de Impacto (`src/corporate_engineer/rag/impact.py`)**:
   - Suporte transparente a `root_path` e métodos de conveniência `analyze_file()` e `analyze_symbol()`.

4. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando oficial `corporate-engineer test-surgical`:
     - Parâmetros: `--base-branch`, `--depth`, `--dry-run`, `--fallback-all`, `--workspace`, `--format text|json`, `--output` e repasse de argumentos adicionais para o pytest.

5. **Arquitetura Formal (ADR-008)**:
   - Formalizada em `docs/adr/ADR-008-surgical-tdd-runner-git-diff.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_surgical_runner.py` foram criados previamente e falharam antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 94 para **99 testes passando** em 24.51s.
- [x] **Cobertura Global**: **88%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 99/99 PASS (`pytest`)
- [x] **Code Linter**: 0 violações (`ruff check .`)
- [x] **Code Formatter**: 59 arquivos verificados e formatados (`ruff format --check .`)
- [x] **Static Type Checker**: 0 erros em 36 arquivos (`mypy .`)
- [x] **Secret Scanner**: 0 credenciais ou tokens expostos (`secret_scanner.py`)
