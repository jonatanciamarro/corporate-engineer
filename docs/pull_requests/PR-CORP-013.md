# Pull Request: feat(system-one): Google Colab SLM fine-tuning notebook & ONNX runtime loader (TRILHA-1)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `TRILHA-1` / `IMP-0014-EXT`
- **Tipo de Alteração**: `feat`
- **Escopo**: `system-one`
- **ADR Associado**: [ADR-013: System-One SLM Fine-Tuning Pipeline, Google Colab Interactive Notebook & ONNX Int8 Runtime Loader](../adr/ADR-013-system-one-slm-training-colab-onnx.md)

---

## 🎯 Resumo das Modificações

Implementação completa da **Trilha 1 do Roadmap Corporativo**, viabilizando o treinamento real do modelo compacto de Sistema 1 no Google Colab (GPU Nvidia T4 gratuita, VRAM < 1.5GB, ~5-8 minutos) e a integração do artefato quantizado ONNX Int8 (`models/model_int8.onnx`) com carregamento preguiçoso (*lazy loading*) e fallback gracioso no framework:

1. **Jupyter Notebook Interativo 1-Clique (`notebooks/train_system_one_colab.ipynb`)**:
   - Badge oficial `Open In Colab` apontando diretamente para o repositório.
   - Instalação automatizada de dependências gratuitas (`transformers`, `peft`, `trl`, `datasets`, `accelerate`, `onnx`, `onnxruntime`).
   - Carregamento de dados com formatação ChatML (`Qwen/Qwen2.5-0.5B-Instruct`).
   - Fine-Tuning com LoRA PEFT ($r=16, \alpha=32$) e `SFTTrainer`.
   - Exportação e quantização dinâmica para ONNX Int8 (`models/model_int8.onnx`).
   - Download automatizado em 1-clique para incorporação direta ao projeto.

2. **Harness de Treinamento e Scripts (`src/corporate_engineer/system_one/trainer.py` e `scripts/train_system_one_colab.py`)**:
   - `SystemOneTrainer.generate_notebook()` gerando notebooks estruturados em `nbformat` v4.
   - Atualização do script de console para consumir o dataset corporativo oficial (`data/system_one_dataset.jsonl`).
   - Suporte a comandos ativos de quantização e salvamento em disco.

3. **Estrutura de Modelos & Runtime Loader (`models/` e `src/corporate_engineer/system_one/nli_engine.py`)**:
   - Criação da pasta `models/` com `.gitkeep` e exclusão de checkpoints transitivos pesados no `.gitignore`.
   - `ONNXNLIDecisionEngine` com lazy loading: valida se `models/model_int8.onnx` existe e se `onnxruntime` está disponível.
   - Fallback transparente e tolerante a falhas: ausência de GPU ou do binário do modelo redireciona automaticamente para o `HeuristicDecisionEngine` com tempo de resposta sub-2ms.

4. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Suporte explícito à flag `--engine onnx` no comando `corporate-engineer decide` (rotas `route`, `risk`, `triage`, `commit`, `skip`).

5. **Infraestrutura de Testes & Resiliência Git (`tests/conftest.py`, `tests/test_system_one_colab_onnx.py`, `src/corporate_engineer/git_utils.py`)**:
   - Resolução de dubious ownership em containers/sandboxes via fixture global de `GIT_CONFIG_GLOBAL`.
   - Proteção contra travamento de rede em testes com `timeout` e `GIT_TERMINAL_PROMPT=0` nas chamadas git.
   - Expansão da suíte para 145 testes automatizados (100% de aprovação e 88% de cobertura).

---

## 🧪 Evidências de Teste & Qualidade

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
plugins: anyio-4.16.0, hypothesis-6.170.17, platformdirs-4.14.8, cov-7.1.0
collected 145 items

145 passed in 19.38s (Suíte 100% verde)
Coverage Global: 88% (2764 statements / 333 misses)
Ruff Linter & Formatter: 0 erros / 0 warnings
Mypy Strict Type Check: Success: no issues found in 53 source files
Pre-Flight Secret Scan: PASS (0 segredos detectados)
```

---

## 🛡️ Checklist de Governança
- [x] ADR-013 documentado em `docs/adr/ADR-013-system-one-slm-training-colab-onnx.md`
- [x] Testes unitários Shift-Left escritos e validados em `tests/test_system_one_colab_onnx.py`
- [x] Zero chamadas bloqueantes ou dependências de rede obrigatórias em ambiente de teste
- [x] Tipagem estrita com Mypy sem erros
- [x] Conformidade com PEP 8 e Ruff
- [x] Branch enviada ao origin antes da emissão da URL de PR
