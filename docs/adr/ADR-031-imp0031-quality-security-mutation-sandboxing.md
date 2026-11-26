# ADR-031: Blindagem de Qualidade, Segurança & Sandboxing de Mutação (IMP-0031)

## Status
Aceito (Accepted)

## Data
2026-11-25

## Contexto & Motivação
A auditoria técnica sênior (97 apontamentos) identificou 4 áreas críticas (Pacote 2) no framework `corporate-engineer` que requeriam blindagem imediata:

1. **PYTHONPATH incorreto no Sandbox de Mutação (`quality/mutation.py`)**:
   O `MutationTestingEngine._run_in_environment()` não inseria `src/` no PYTHONPATH ao copiar o workspace para o sandbox temporário, causando a execução de testes de mutação contra o código original (não-mutado) em editable installs, invalidando o Mutation Score.

2. **Regexes de Segredos desatualizadas (`secret_scanner.py`, `tool_security_guard.py`)**:
   O padrão OpenAI (`sk-[A-Za-z0-9]{20,}`) não cobria chaves modernas com prefixos `sk-proj-`, `sk-svcacct-` e `sk-live-`. O padrão Anthropic não cobria `sk-ant-api03-`. Três cópias dos regexes existiam sem sincronização.

3. **`is_path_safe()` vulnerável no Storage Cleaner (`quality/storage_cleaner.py`)**:
   Aceitava raízes de disco (`C:\`, `/`), `Path.home()`, ancestrais do workspace, diretórios de sistema operacional e symlinks, permitindo deleção catastrófica.

4. **`re_verify()` mockado no Adversarial (`orchestrator/adversarial.py`)**:
   A Fase 1.7 (re-verificação adversarial) retornava sempre `is_blocked=False` sem análise real, neutralizando o loop dialético de blindagem.

## Decisão de Arquitetura

### 1. Correção de PYTHONPATH no Sandbox de Mutação
- `_run_in_environment()` insere `effective_ws / "src"` como PRIMEIRO elemento do PYTHONPATH, seguido de `effective_ws`, seguido do parent flat-layout (somente se não estiver dentro de `src/` e sem `__init__.py`).
- Adicionados `.ruff_cache` e `.cache` ao `shutil.copytree` ignore.
- Adicionado guarda contra shadowing de stdlib por namespace packages PEP 420.

### 2. Sincronização de Regexes de Segredos
- OpenAI: `r"\bsk-(?!ant-)(?:proj-|svcacct-|live-)?[A-Za-z0-9_\-]{32,}\b"` — cobre `sk-proj-*`, `sk-svcacct-*`, `sk-live-*` e clássicas, sem false-positive em Anthropic via negative lookahead.
- Anthropic: `r"\bsk-ant-(?:api\d{2}-)?[A-Za-z0-9_\-]{32,}\b"` — cobre `sk-ant-api03-*` e futuras versões `apiNN`.
- AWS Key fallback: `{16}` → `{16,}` para cobertura de chaves mais longas.
- Todas as 3 cópias (`secret_scanner.py` lib, `secret_scanner.py` script, `tool_security_guard.py`) sincronizadas.

### 3. Blindagem do `is_path_safe()` no Storage Cleaner
13 camadas de proteção:
- Rejeição de raízes de disco e UNC roots
- Rejeição de `Path.home()` e seus ancestrais
- Rejeição de ancestrais do workspace
- Rejeição de diretórios de sistema (Windows: `Windows`, `Program Files`, `System32`; POSIX: `/bin`, `/sbin`, `/usr`, `/lib`, `/boot`)
- `FORBIDDEN_DIR_NAMES` expandido com `.gnupg`, `.kube`, `.git`
- `CRITICAL_SYSTEM_ROOT_DIRS` para raízes do sistema
- Containers de usuários (profundidade ≤ 3)
- `var`/`private` (exceto subdiretórios de `tempfile.gettempdir()`)
- Rejeição de symlinks (`raw_candidate.is_symlink()`)
- Rejeição do diretório raiz de temp (`tempfile.gettempdir()`)
- Detecção de OneDrive (`"onedrive - "`)

### 4. Re-Verificação Adversarial Genuína (Fase 1.7)
- `_ReVerifyContext` dataclass centralizando estado de re-verificação
- 5 etapas de validação: risco residual, cobertura de ataque, substância de hardening, sinais de categoria, varredura de ameaças arquiteturais
- `_scan_architecture_threats()` com filtro de padrões benignos quando categoria já mitigada
- `_run_hardening_rounds()` com loop boundado de 2 rodadas e refinamento de `attack_report`
- `ArchitectureTranscender.transcend()` com `arch_summary` construído a partir de hardenings reais

## Consequências

### Positivas
- Mutation Score confiável com testes executando contra código realmente mutado
- Cobertura de 100% dos padrões modernos de API keys (OpenAI, Anthropic, AWS)
- Proteção contra deleção acidental de diretórios críticos do sistema
- Loop dialético adversarial completo com re-verificação genuína em 5 etapas

### Riscos
- `is_path_safe()` pode bloquear falsamente diretórios legítimos em edge cases extremos; prefere-se false-positive a false-negative (princípio fail-safe)
- `re_verify()` pode gerar false-positives em transcendence plans com vocabulário técnico ambíguo; filtro de benign patterns mitiga isso

## Evidências
- 361/361 testes PASS em 68.50s (incluindo 52 novos casos de teste em `tests/test_imp0031_*.py`)
- 0 erros Ruff check / format (175 arquivos verificados e formatados)
- 0 erros Mypy (105 arquivos fonte)
- 0 segredos detectados (`secret_scanner.py`)
- 48/48 módulos auto-wired (`audit --wiring` `passed: true`)
- Semantic Eval (`src/corporate_engineer/`): 93.1 / 100.0 (Grade A) PASS
