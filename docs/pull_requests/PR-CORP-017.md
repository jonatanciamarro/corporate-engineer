# Pull Request: feat(ci): GitHub Actions workflow de auto-remediação em PRs (IMP-0017)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0017`
- **Tipo de Alteração**: `feat`
- **Escopo**: `ci`
- **ADR Associado**: [ADR-017: GitHub Actions Workflow de Auto-Remediação em PRs (self-heal.yml)](../adr/ADR-017-github-actions-self-healing-ci.md)

---

## 🎯 Resumo das Modificações

Implementação do **GitHub Actions Workflow de Auto-Remediação em PRs (IMP-0017)**, automatizando a execução do motor de auto-cura de AST (`ASTSelfHealingFixer` / `corporate-engineer fix --auto`) diretamente nas submissões e atualizações de Pull Requests no GitHub:

1. **Workflow de Integração Contínua (`.github/workflows/self-heal.yml`)**:
   - Disparo direcionado para eventos `pull_request` (`opened`, `synchronize`, `reopened`) apontando para `main`.
   - Permissões mínimas de privilégio: `contents: write` e `pull-requests: write`.
   - Checkout do branch do PR (`ref: ${{ github.head_ref }}`) com histórico completo (`fetch-depth: 0`).
   - Setup automatizado de Python 3.11 com cache de dependências pip.
   - Instalação e execução de `corporate-engineer fix --auto --path src/`.
   - Identificação de diffs locais via `git status --porcelain src/` e commit assinado por `github-actions[bot]`.
   - Mecanismo de prevenção contra loops recursivos de CI via trailer `[skip ci]` no commit e push direto para o branch de origem.
   - Auditoria final estrita com `corporate-engineer audit --strict`.

2. **Suíte de Testes Automatizados (Shift-Left TDD)**:
   - Implementação de `tests/test_self_heal_workflow.py` com 5 testes automatizados:
     - `test_self_heal_workflow_file_exists`: Garante presença do workflow no caminho canônico.
     - `test_self_heal_workflow_yaml_syntax`: Validação estrita do schema e tipagem YAML.
     - `test_self_heal_workflow_triggers`: Validação dos eventos disparadores de PR.
     - `test_self_heal_workflow_job_structure`: Verificação dos passos fundamentais de remediação e proteção contra loops.
     - `test_self_healing_cli_integration`: Teste prático de ponta a ponta com código degradado curado via `corporate-engineer fix`.
   - Expansão da suíte global para **184 testes automatizados** (100% PASS).

---

## 🧪 Evidências de Teste & Qualidade

```text
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.2.0, pluggy-1.7.0
plugins: hypothesis-6.168.5, cov-7.1.0
collected 184 items

tests\test_ast_indexer.py ......                                         [  3%]
tests\test_cached_ast_indexer.py ....                                    [  5%]
tests\test_circuit_breaker.py .......                                    [  9%]
tests\test_cli.py .......................                                [ 21%]
tests\test_eval.py .....                                                 [ 24%]
tests\test_fixer.py ........                                             [ 28%]
tests\test_impact.py ....                                                [ 30%]
tests\test_mcp_client.py .........                                       [ 35%]
tests\test_mcp_hub.py ......                                             [ 39%]
tests\test_metaprompt_engine.py .........                                [ 44%]
tests\test_models.py ........                                            [ 48%]
tests\test_mutation.py .....                                             [ 51%]
tests\test_orchestrator.py ...........                                   [ 57%]
tests\test_pr_link.py ........                                           [ 61%]
tests\test_quality_gate.py ..                                            [ 62%]
tests\test_self_heal_workflow.py .....                                   [ 65%]
tests\test_stack_detector.py ...                                         [ 66%]
tests\test_storage_cleaner.py ..........                                 [ 72%]
tests\test_surgical_runner.py .....                                      [ 75%]
tests\test_swarm_coordinator.py ........                                 [ 79%]
tests\test_system_one.py ..........                                      [ 84%]
tests\test_system_one_benchmark.py .......                               [ 88%]
tests\test_system_one_colab_onnx.py .......                              [ 92%]
tests\test_system_one_pipeline.py ........                               [ 96%]
tests\test_telemetry.py ......                                           [100%]

============================ 184 passed in 19.75s =============================

Ruff Linter & Formatter: 0 erros / 106 arquivos verificados e formatados
Mypy Strict Type Check: Success: no issues found in 63 source files
Pre-Flight Secret Scanner: PASS (0 segredos ou credenciais expostas)
```

---

## 🚀 Como Testar Localmente

```bash
# Executar a suíte de testes do workflow de auto-remediação
.venv\Scripts\pytest tests/test_self_heal_workflow.py -v

# Simular a auto-cura da CLI localmente
.venv\Scripts\python -m corporate_engineer.cli fix --path src/ --auto

# Executar a auditoria estrita que roda no workflow
.venv\Scripts\python -m corporate_engineer.cli audit --strict
```
