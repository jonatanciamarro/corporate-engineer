# PR: feat(quality,security): IMP-0031 quality hardening, secret scanner regex, mutation sandbox, adversarial Phase 1.7 (IMP-0031 / ADR-031)

## 📌 Resumo das Modificações
Implementação do **Pacote 2 de Blindagem de Qualidade, Segurança e Sandboxing de Mutação** no framework `corporate-engineer`, em conformidade com o **ADR-031**:

1. **Sandboxing de Mutação com PYTHONPATH Fiel (`quality/mutation.py`)**:
   - `_run_in_environment()` agora injeta `effective_ws / "src"` como primeira entrada de `PYTHONPATH`, seguida por `effective_ws` e pelo parent flat-layout apenas quando aplicável (fora de `src/` e sem `__init__.py`).
   - Adição de `.ruff_cache` e `.cache` aos padrões ignorados no `shutil.copytree`, rastreamento explícito de `copytree_succeeded` com cópia fallback do arquivo de teste e guarda contra shadowing de stdlib por namespace packages PEP 420.

2. **Blindagem e Sincronização de Scanner de Segredos (`quality/secret_scanner.py`, `quality/tool_security_guard.py`, `.agents/skills/corp-pipeline/scripts/secret_scanner.py`)**:
   - OpenAI API Key atualizada para `\bsk-(?!ant-)(?:proj-|svcacct-|live-)?[A-Za-z0-9_\-]{32,}\b` (cobrindo `sk-proj-`, `sk-svcacct-`, `sk-live-` com hífens/underscores e sem colidir com chaves Anthropic).
   - Anthropic API Key atualizada para `\bsk-ant-(?:api\d{2}-)?[A-Za-z0-9_\-]{32,}\b` (cobrindo `sk-ant-api03-` e futuras versões).
   - Fallback de AWS Access Key ajustado de `{16}` para `{16,}` em `tool_security_guard.py` e no script `secret_scanner.py`.
   - Todas as 3 cópias e fallbacks sincronizados de ponta a ponta.

3. **Proteção em 13 Camadas no Storage Cleaner (`quality/storage_cleaner.py`)**:
   - `is_path_safe()` e `clean_target()` passam a rejeitar raízes de disco/UNC, `Path.home()` e seus ancestrais, ancestrais do workspace, diretórios críticos do SO (Windows e POSIX), `FORBIDDEN_DIR_NAMES` (`.gnupg`, `.kube`, `.git`), containers de usuários em profundidade ≤ 3, `var`/`private` fora de `tempfile.gettempdir()`, raiz de temp (`tempfile.gettempdir()`), prefixo `"onedrive - "` e symlinks (`raw_candidate.is_symlink()`).

4. **Re-Verificação Adversarial Genuína na Fase 1.7 (`orchestrator/adversarial.py`)**:
   - Substituição do stub permissivo de `AdversarialRedTeam.re_verify()` por verificação estruturada em 5 etapas (risco residual, cobertura dos achados do ataque, substância de hardening contra placeholders/negações, sinais obrigatórios por categoria e varredura de novas ameaças na arquitetura transcendida).
   - Construção de `arch_summary` real em `ArchitectureTranscender.transcend()` e refinamento iterativo em `AdversarialLoopCoordinator._run_hardening_rounds()` (limite de 2 rodadas), resolvendo integralmente os apontamentos da Revisão Sênior (HIGH #1, MEDIUM #2/#3, LOW #7).

5. **Configuração de Infraestrutura Local (fora do código-fonte)**:
   - Ajuste dos comandos em `.agents/hooks.json` para `py orchestration/hooks/run_hook.py <hook>` (adequação ao CWD `.agents/` dos hooks no ambiente Windows Sandbox).

6. **Shift-Left TDD (`tests/test_imp0031_*.py`)**:
   - 52 novos casos de teste parametrizados e unitários distribuídos em `test_imp0031_mutation_sandbox.py` (7), `test_imp0031_security_and_storage.py` (20) e `test_imp0031_adversarial_reverification.py` (25).

> **Observação Residual (Fora de Escopo IMP-0031)**: `src/corporate_engineer/lora/exporter.py` (linha 17) ainda utiliza o padrão legado `sk-[0-9A-Za-z]{20,}` no redator de exportação LoRA; registrado para avaliação futura sem alteração unilateral.

---

## 🧪 Plano de Testes & Validação

- [x] Sandbox de mutação (`tests/test_imp0031_mutation_sandbox.py` — 7 casos)
- [x] Regexes modernas OpenAI/Anthropic/AWS e `SafeStorageCleaner` (`tests/test_imp0031_security_and_storage.py` — 20 casos)
- [x] Loop dialético Fase 1.7 e apontamentos de revisão sênior (`tests/test_imp0031_adversarial_reverification.py` — 25 casos)
- [x] Pre-Flight Gate 100% verde:
  - `pytest -q`: **361 passed in 68.50s**
  - `ruff check .`: 0 erros (`All checks passed!`)
  - `ruff format --check .`: 175 arquivos formatados
  - `mypy .`: 0 erros em 105 arquivos fonte
  - `secret_scanner.py .`: 0 credenciais detectadas (`PASS`)
  - `corporate-engineer audit --wiring --format json`: 48/48 módulos conectados (`passed: true`)
  - `corporate-engineer eval src/corporate_engineer/`: **93.1 / 100.0 [Grade: A] PASS**
