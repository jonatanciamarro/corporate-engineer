# PR-CORP-022: Tratamento Robusto de Timeouts Git e Eliminação de Erros Silenciosos no Pre-Flight

## Tipo de Mudança
- [x] `fix`: Eliminação de erros silenciosos e mascaramento de falhas de rede Git
- [x] `feat`: Timeouts configuráveis, execução segura com `shell=False` no QualityGate e logging estruturado
- [ ] `refactor`: Refatoração estrutural
- [x] `test`: Novos testes automatizados (Shift-Left TDD)
- [x] `docs`: Formalização do ADR-024

## Ticket / ID da Proposta
- **ID**: `IMP-0022`
- **Referência ADR**: [ADR-024](../../docs/adr/ADR-024-robust-git-timeouts-preflight.md)
- **Status do Backlog**: `IMPLEMENTED`

---

## Descrição do Pull Request

Este Pull Request implementa a resolução estrutural das vulnerabilidades de tratamento de exceções silenciosas e timeouts agressivos identificadas na auditoria técnica profunda via Swarm (`relatorio_auditoria_swarm.md`):

1. **Robustez de Timeouts Git com Logging Estruturado (`src/corporate_engineer/git_utils.py`)**:
   - Inclusão de `logger = logging.getLogger(__name__)`.
   - Adição do parâmetro `timeout: float = 15.0` em `is_branch_pushed` e `push_branch_to_remote`, com resolução dinâmica da variável de ambiente `CORP_GIT_TIMEOUT`.
   - Tratamento explícito de `subprocess.TimeoutExpired` emitindo advertências descritivas em vez de capturas genéricas que retornavam `False` sem rastro.
   - Diagnósticos transparentes em `get_remote_url` e `extract_github_repo_slug` quando a identificação do remote falhar, evitando fallbacks fixos pessoais silenciosos.

2. **Transparência e Resiliência no `SurgicalTestRunner` (`src/corporate_engineer/quality/surgical_runner.py`)**:
   - Eliminação de blocos `pass` cegos em `collect_changed_files`, passando a registrar avisos com `logger.warning("Git subprocess error in %s: %s", cmd, exc)`.
   - Suporte a timeout de 15.0s em comandos Git.
   - Verificação de plataforma `os.name == "nt"` antes de tentar caminhos `.venv/Scripts/pytest.exe` para portabilidade limpa entre POSIX e Windows.

3. **Execução Segura com `shell=False` no Quality Gate (`src/corporate_engineer/quality/gate.py`)**:
   - `QualityGateRunner.run_tests` refatorado para executar comandos com `shell=False` usando listas de argumentos seguros com parsing via `shlex.split`.
   - Suporte a timeout configurável (`timeout: float = 120.0`).
   - Tratamento especializado de `subprocess.TimeoutExpired` retornando `exit_code=-2` e `stderr=f"Command timed out after {timeout}s"`.
   - Otimização do scanner de segredos para ignorar diretórios internos (`.git`, `.venv`, `__pycache__`, `node_modules`).

4. **Suíte Abrangente de Shift-Left TDD (`tests/test_git_robustness_and_silent_errors.py`)**:
   - 6 novos testes unitários validando tratamento de `TimeoutExpired`, precedência de `CORP_GIT_TIMEOUT`, logging de warnings em comandos Git e runner cirúrgico, e execução com `shell=False` no QualityGate.
   - Suíte global expandida para **261/261 testes PASS** em 45.35s.

---

## Verificações de Pre-Flight (100% Aprovadas)

- [x] **Testes Automatizados**: `pytest` (261/261 PASS)
- [x] **Linter & Formatação**: `ruff check .` e `ruff format --check .` (0 erros)
- [x] **Tipagem Estática**: `mypy .` (0 erros em 79 arquivos)
- [x] **Pre-Flight Secret Scan**: `secret_scanner.py` (0 vazamentos)
