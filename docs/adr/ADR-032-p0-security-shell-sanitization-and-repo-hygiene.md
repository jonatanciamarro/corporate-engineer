# ADR-032: Hardening de Execução Shell no MCP Local, Unificação de Secrets LoRA & Higiene de Portfólio (Pacote P0: IMP-0034 + IMP-0035)

## Status
Aceito (Accepted) — Aguardando Gate 1 do `corp-pipeline` para Execução

## Data
2026-11-26

## Contexto & Motivação
A avaliação técnica do repositório sob ótica de entrevista sênior identificou bloqueadores imediatos de segurança, integridade de segredos e apresentação no GitHub (**Pacote P0**):

1. **Command Injection em `LocalMCPToolAdapter._handle_shell()` (`src/corporate_engineer/mcp/client.py:143-173`)**:
   O adaptador valida apenas o primeiro token (`tokens[0]`) contra `SAFE_COMMAND_PREFIXES`, mas executa a string completa via `subprocess.run(cmd, shell=True, ...)`. Isso permite bypass trivial por encadeamento de shell (`pytest && whoami`, `;`, `|`, redirecionamentos, backticks, `$()`) ou execução inline arbitrária (`python -c ...`).
2. **Regex Legado no Exportador LoRA (`IMP-0034` — `src/corporate_engineer/lora/exporter.py:13-18`)**:
   `LoraVertexExporter` mantém lista isolada `SECRET_PATTERNS` com `sk-[0-9A-Za-z]{20,}`, deixando escapar chaves modernas com hífen/underscore (`sk-proj-...`, `sk-svcacct-...`, `sk-live-...`, `sk-ant-api03-...`) ao gerar arquivos `.jsonl`.
3. **Higiene de Repositório & `README.md` Desalinhado**:
   - `src/corporate_engineer.egg-info/` está rastreado no Git (gerando commits espúrios de bot como `751ae2a`).
   - Registros em `.agents/orchestration/` contêm paths absolutos locais (`file:///e:/projcts/corporate%20engineer/...`).
   - Scripts e documentos pessoais de otimização Windows (`scripts/optimize_windows_for_ai_dev.ps1`, `scripts/start_interview_mode.ps1`, `scripts/stop_interview_mode.ps1`, `docs/architecture/windows_optimization_architecture.md`, `tests/test_windows_optimization_scripts.py`) poluem o escopo do framework corporativo.
   - `README.md` documenta apenas 3 skills e 2 scripts auxiliares, omitindo o pacote Python `corporate_engineer`, a CLI modular, instalação, arquitetura e o status real de cada módulo.

## Decisão de Arquitetura

### 1. Hardening Estrito de `_handle_shell()` em `LocalMCPToolAdapter`
- **Parsing sem shell**: Substituir `cmd.split()` + `shell=True` por `shlex.split(cmd, posix=(os.name != "nt"))` e `subprocess.run(tokens, shell=False, ...)`.
- **Bloqueio de Metacaracteres & Subshells**: Rejeitar comandos contendo operadores/metacaracteres (`&&`, `||`, `;`, `|`, `>`, `<`, `` ` ``, `$(`, `\n`, `\r`).
- **Bloqueio de Execução Inline em Interpretadores**: Para binários interpretadores (`python`, `python3`, etc.), rejeitar flags de código inline (`-c`, `--command`, `-e`, `--eval`) e leitura de stdin (`-`), preservando chamadas legítimas como `python --version` ou `python -m pytest`.
- **Resolução Segura de Executável no Windows/POSIX**: Garantir que `python` utilize `sys.executable` (ou resolução via `shutil.which(..., path=env["PATH"])`) para compatibilidade com `shell=False` no Windows.

### 2. Fonte Única de Verdade para Detecção de Segredos (`IMP-0034`)
- Substituir a lista local `SECRET_PATTERNS` de `src/corporate_engineer/lora/exporter.py` por reutilização direta de `CanonicalSecretScanner` (`src/corporate_engineer/quality/secret_scanner.py`), garantindo cobertura imediata e sincronizada de OpenAI (`sk-proj-`, `sk-svcacct-`, `sk-live-`), Anthropic (`sk-ant-api03-`), AWS, GitHub, GitLab, Gemini, Slack, Stripe e chaves privadas.

### 3. Higiene de Repositório, Remoção de Artefatos Pessoais & Novo `README.md`
- Remover `src/corporate_engineer.egg-info/` do índice Git (`git rm -r --cached src/corporate_engineer.egg-info`), preservando a regra `*.egg-info/` no `.gitignore`.
- Remover os arquivos pessoais de tuning Windows (`scripts/optimize_windows_for_ai_dev.ps1`, `scripts/start_interview_mode.ps1`, `scripts/stop_interview_mode.ps1`, `docs/architecture/windows_optimization_architecture.md`, `tests/test_windows_optimization_scripts.py`).
- Converter todos os links `file:///e:/projcts/corporate%20engineer/...` nos registros `.agents/orchestration/` para caminhos relativos portáveis.
- Reescrever `README.md` com visão técnica objetiva: propósito do framework, arquitetura de `src/corporate_engineer/`, instalação, comandos da CLI, qualidade/testes e seção transparente de maturidade dos módulos (determinístico/AST vs protótipos/stubs em evolução).

## Alternativas Consideradas
- **Opção A (Escolhida)**: `shell=False` + `shlex.split` + bloqueio de metacaracteres e inline `-c`/`-e` + remoção completa dos scripts pessoais Windows + `CanonicalSecretScanner` compartilhado. Máxima segurança e portabilidade mantendo a API existente de `LocalMCPToolAdapter`.
- **Opção B**: Bloquear apenas `&&`/`;` mantendo `python -c` e movendo os scripts Windows para `examples/`. Rejeitada por manter vetor RCE trivial via `python -c` e manter código fora do domínio do projeto.

## Consequências

### Positivas
- Eliminação completa de command injection no `LocalMCPToolAdapter`.
- Zero drift entre o scanner de pre-flight e o sanitizador de exportação LoRA (`IMP-0034`).
- Repositório portável, sem caminhos locais hardcoded, sem `egg-info` versionado e com `README.md` fiel ao código real.

### Riscos e Mitigações
- **Risco**: Comandos Windows com `shell=False` exigem que o binário exista no `PATH` (ex.: `pytest.exe` ou `git.exe`) — `shutil.which` sobre `env["PATH"]` e uso de `sys.executable` para `python` mitigam qualquer falha de resolução no Windows.
- **Risco**: Remoção de `tests/test_windows_optimization_scripts.py` reduz a contagem nominal de testes (de 361 para 352 antes dos novos testes de segurança P0), mas elimina testes de escopo alheio ao framework; os novos testes TDD de segurança e LoRA repõem cobertura relevante no core.
