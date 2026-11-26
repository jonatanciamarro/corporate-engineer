# PR: feat(cli,rag,system-one): Onda P1 — integridade CLI/Hooks, RAG cache, LoRA generics e System-One honesto (IMP-0032 / IMP-0033 / IMP-0036 / ADR-033)

## 📌 Resumo das Modificações
Implementação da **Onda P1** coordenada via Swarm multi-agente em conformidade com o **ADR-033**:

1. **CLI & Hooks Dinâmicos (`IMP-0032`)**:
   - `.agents/orchestration/hooks/run_hook.py`: descoberta dinâmica segura (`^[a-zA-Z0-9_]+$`) via `importlib.util` e `runpy.run_path`, eliminando whitelist estática e bloqueando path traversal.
   - `src/corporate_engineer/cli/commands/rag.py`: `handle_eval()` valida existência do alvo retornando exit code `1`; `index` e `blast-radius` isolam mensagens `--output` em `sys.stderr` no modo JSON.
   - `src/corporate_engineer/cli/commands/prompt.py`: isolamento `sys.stderr` em `--format json --output`.
   - `src/corporate_engineer/cli/commands/mcp.py`: erro explícito (`exit 1`) quando subcomando é omitido.
2. **RAG Cache, LoRA TS Generics & Refiner (`IMP-0033`)**:
   - `src/corporate_engineer/rag/cached_ast_indexer.py`: correção de *cache starvation* em `get_all_symbol_names()` com varredura incremental SHA-256 e poda de entradas obsoletas.
   - `src/corporate_engineer/lora/validator.py`: reconhecimento de generics TypeScript em `validate_remotion_syntax()` sem perder detecção de tags JSX inválidas.
   - `src/corporate_engineer/prompt/refiner.py`: atualização da referência obsoleta `cli.py` para `cli/parser.py` e `cli/main.py`.
3. **Integridade System-One & Benchmark (`IMP-0033` + `IMP-0036`)**:
   - `src/corporate_engineer/system_one/benchmark.py`: acurácia calculada sobre `max(total_runs, 1)` e recomendações fiéis ao motor efetivo.
   - `src/corporate_engineer/system_one/nli_engine.py`: lazy-loading thread-safe (`RLock`) + suporte a `session`/`tokenizer` para inferência ONNX real (`onnx-nli`) e transparência de fallback (`heuristic-fallback`).
   - `src/corporate_engineer/system_one/outlines_engine.py`: cache thread-safe de modelo em `self._model` e suporte a `decide_noul`/`decide_score`.
   - `src/corporate_engineer/system_one/trainer.py` & `scripts/train_system_one_colab.py`: exportação/quantização Int8 real via `merge_and_unload()` + `optimum.onnxruntime` (`ORTModelForCausalLM`, `ORTQuantizer`).

---

## 🧪 Plano de Testes & Validação

- [x] Shift-Left TDD (`tests/test_hook_resilience_and_rule_triggers.py`, `tests/test_cli.py`, `tests/test_cached_ast_indexer.py`, `tests/test_gemini_lora_pipeline.py`, `tests/test_metaprompt_engine.py`, `tests/test_system_one.py`, `tests/test_system_one_benchmark.py`, `tests/test_system_one_colab_onnx.py`).
- [x] Pre-Flight Gate verificado (`verifier`):
  - `ruff check .`: 0 erros (`All checks passed!`)
  - `ruff format --check .`: 0 erros (`177 files already formatted`)
  - `mypy .`: 0 erros (`104 source files`)
  - `secret_scanner.py .`: `PASS` (`0` segredos)
  - `corporate-engineer audit --wiring`: `PASS`
  - `pytest -q`: **380 passed in 174.12s**
