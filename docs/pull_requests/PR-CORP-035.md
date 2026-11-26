# PR: fix(security,chore): Pacote P0 — hardening shell=False no MCP local, IMP-0034 secrets LoRA, higiene Git & README (IMP-0034 / IMP-0035 / ADR-032)

## 📌 Resumo das Modificações
Implementação do **Pacote P0** de correções prioritárias derivadas da auditoria de portfólio/entrevista técnica, em conformidade com o **ADR-032**:

1. **Eliminação de Command Injection no `LocalMCPToolAdapter` (`src/corporate_engineer/mcp/client.py`)**:
   - Substituição de `subprocess.run(cmd, shell=True)` por `shlex.split` + `shell=False`.
   - Bloqueio explícito de metacaracteres de shell (`&&`, `||`, `;`, `|`, `>`, `<`, `` ` ``, `$(`, `\n`, `\r`) e flags de execução inline em interpretadores (`-c`, `-e`, `--command`, `--eval`, `-`).
   - Resolução segura de binários via `sys.executable` (Python) e `shutil.which`.
2. **Unificação Canônica de Segredos no `LoraVertexExporter` (`IMP-0034` — `src/corporate_engineer/lora/exporter.py`)**:
   - Remoção do regex legado `sk-[0-9A-Za-z]{20,}` e adoção direta de `SECRET_PATTERNS` de `corporate_engineer.quality.secret_scanner`.
3. **Higiene do Repositório & Novo `README.md`**:
   - Remoção de `src/corporate_engineer.egg-info/` do índice Git (`git rm -r --cached`) e inclusão de `models/*.zip` no `.gitignore`.
   - Remoção dos scripts, documentação e testes pessoais de tuning Windows (`scripts/optimize_windows_for_ai_dev.ps1`, `scripts/start_interview_mode.ps1`, `scripts/stop_interview_mode.ps1`, `docs/architecture/windows_optimization_architecture.md`, `tests/test_windows_optimization_scripts.py`).
   - Conversão de links `file:///e:/projcts/...` para caminhos relativos portáveis nos registros `.agents/orchestration/`.
   - Reescrita do `README.md` refletindo a arquitetura real do pacote Python, CLI, instalação e matriz honesta de maturidade dos módulos.
   - Catalogação formal das ondas P0–P3 (`IMP-0035` a `IMP-0041`) em `.agents/orchestration/improvement-backlog.md`.

---

## 🧪 Plano de Testes & Validação

- [x] Shift-Left TDD (`tests/test_mcp_client.py`): bloqueio de injeções (`&&`, `;`, `|`, `>`, backticks, `$()`, `python -c`) e garantia de `shell=False` com lista de argumentos.
- [x] Shift-Left TDD (`tests/test_gemini_lora_pipeline.py`): redação de chaves modernas `sk-proj-`, `sk-svcacct-`, `sk-live-` e `sk-ant-api03-`.
- [x] Pre-Flight Gate verificado após correção final:
  - `ruff check .`: 0 erros
  - `ruff format --check .`: 0 erros
  - `mypy .`: 0 erros em 104 arquivos fonte
  - `secret_scanner.py .`: 0 segredos detectados (`PASS`)
  - `corporate-engineer audit --wiring`: `PASS`
  - `pytest -q`: **355 passed**
