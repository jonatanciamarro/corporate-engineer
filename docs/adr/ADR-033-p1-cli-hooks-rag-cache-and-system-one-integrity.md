# ADR-033: Integridade de CLI/Hooks, Correções de RAG/Benchmark/LoRA & Honestidade System-One (Onda P1: IMP-0032 + IMP-0033 + IMP-0036)

## Status
Aceito (Accepted) — Aguardando Gate 1 do `corp-pipeline` para Execução

## Data
2026-11-26

## Contexto & Motivação
A Onda P1 consolida três trilhas críticas identificadas na auditoria técnica e no backlog (`IMP-0032`, `IMP-0033` e `IMP-0036`):

1. **Integridade da CLI & Dispatch Dinâmico de Hooks (`IMP-0032`)**:
   - `.agents/orchestration/hooks/run_hook.py` mantém lista `if/elif` estática para execução in-process, rejeitando novos hooks adicionados em `.agents/orchestration/hooks/`.
   - `cli/commands/prompt.py` (e helpers em `cli/commands/rag.py`) emitem mensagens informativas no `stdout` junto com `--format json`, quebrando parsers JSON em pipelines Unix.
   - `cli/commands/rag.py:handle_eval()` aprova diretórios inexistentes retornando nota `100.0` (Grade `A`) e exit code `0`.
   - `cli/commands/mcp.py` retorna exit code `0` silenciosamente quando chamado sem subcomando (`corporate-engineer mcp`).

2. **RAG Cache Starvation, Benchmark, LoRA JSX & Refiner (`IMP-0033`)**:
   - `CachedASTCodebaseIndexer.get_all_symbol_names()` (`src/corporate_engineer/rag/cached_ast_indexer.py`) verifica `if not names:`, causando *cache starvation*: se ao menos um arquivo estiver em cache, o restante da base nunca é indexado.
   - `SystemOneBenchmark.run()` (`src/corporate_engineer/system_one/benchmark.py`) calcula `accuracy_percent` dividindo por `successful_runs` em vez de `total_runs`, inflando acurácia quando há falhas.
   - `LoraSyntaxValidator.validate_remotion_syntax()` (`src/corporate_engineer/lora/validator.py`) confunde generics TypeScript (`useState<number>(0)`, `Array<string>`, `React.FC<Props>`) com tags JSX abertas.
   - `ContextAwarePromptRefiner.DOMAIN_KEYWORDS["cli"]["modules"]` (`src/corporate_engineer/prompt/refiner.py:100`) aponta para o arquivo deletado `src/corporate_engineer/cli.py`.

3. **Integridade & Honestidade dos Motores `System-One` (`IMP-0036`)**:
   - `ONNXNLIDecisionEngine` (`src/corporate_engineer/system_one/nli_engine.py`) delega 100% para `HeuristicDecisionEngine` mesmo quando `has_model()` é `True`, e ainda reporta `engine_name="onnx-nli"`.
   - `OutlinesDecisionEngine` (`src/corporate_engineer/system_one/outlines_engine.py`) reinstancia `outlines.models.transformers(...)` a cada chamada de `decide_choice()`, sem cache de instância.
   - `SystemOneTrainer.generate_colab_recipe()` (`src/corporate_engineer/system_one/trainer.py`) e `scripts/train_system_one_colab.py` apenas imprimem sucesso na etapa 4 sem exportar/quantizar o modelo para ONNX Int8.

## Decisão de Arquitetura

### 1. Hooks Dinâmicos & CLI POSIX (`IMP-0032`)
- **Dispatch dinâmico seguro em `run_hook.py`**: Validar nome do hook (`^[a-zA-Z0-9_]+$`, bloqueando traversal), localizar `<hooks_dir>/<hook_name>.py`, carregar via `importlib.util.spec_from_file_location` e invocar `run_<hook_name>_hook()` se presente, ou executar via `runpy.run_path(..., run_name="__main__")`.
- **Contratos CLI**:
  - `handle_eval`: verificar `target.exists()`; retornar `1` com mensagem clara em `sys.stderr` (ou JSON estruturado de erro se `--format json`) quando ausente.
  - `mcp`: tornar `mcp_action` obrigatório (`mcp_subparsers.required = True` ou retornar `1` com usage em `sys.stderr`).
  - `prompt` e `rag`: redirecionar mensagens `[✓]` / `✅` para `sys.stderr` sempre que `--format json` estiver ativo com `--output`, mantendo `stdout` estritamente JSON válido.

### 2. Correções Core RAG / Benchmark / LoRA / Refiner (`IMP-0033`)
- **`CachedASTCodebaseIndexer.get_all_symbol_names()`**: Varrer os arquivos `.py` do `root_path` ignorando diretórios de build/venv e invocar `self.index_file(full_p)` (hit O(1) via SHA-256 para arquivos inalterados e indexação incremental para novos/modificados), além de remover entradas obsoletas de arquivos apagados.
- **`SystemOneBenchmark.run()`**: Calcular `accuracy = round((correct_runs / max(total_runs, 1)) * 100.0, 2)` usando `total_runs` como denominador.
- **`LoraSyntaxValidator.validate_remotion_syntax()`**: Ignorar expressões TypeScript generics (`<Type>` precedidas por identificador/tipo/palavra-chave TS ou seguidas por `(`, `,`, `;`, `=`, `)`, `|`, `&`, `extends`, `:`, `[`) na verificação de balanceamento de tags JSX.
- **`ContextAwarePromptRefiner`**: Atualizar `DOMAIN_KEYWORDS["cli"]["modules"]` para `["src/corporate_engineer/cli/parser.py", "src/corporate_engineer/cli/main.py"]`.

### 3. System-One Genuíno e Honesto (`IMP-0036`)
- **`ONNXNLIDecisionEngine`**:
  - Implementar carregamento lazy thread-safe (`threading.RLock`) de `onnxruntime.InferenceSession` + `tokenizers.Tokenizer` (com injeção opcional de `session` e `tokenizer` para testabilidade sem exigir runtime pesado instalado).
  - Quando `session` + `tokenizer` estiverem carregados, executar inferência real de logits/score para `decide_choice`, `decide_noul` e `decide_score`, reportando `engine_name="onnx-nli"`.
  - Sempre que a execução recorrer ao `HeuristicDecisionEngine`, reportar **exclusivamente** `engine_name="heuristic-fallback"` (nunca `"onnx-nli"`).
- **`OutlinesDecisionEngine`**:
  - Adicionar cache lazy thread-safe (`self._model`, `self._generators`) por `model_id` para evitar recarregamento por chamada, estendendo uso para `decide_noul` e `decide_score` quando disponível.
  - Reportar `engine_name="outlines"` apenas quando a inferência real (ou `generator_override`) executar; caso contrário reportar `"heuristic-fallback"`.
- **`SystemOneTrainer` & `scripts/train_system_one_colab.py`**:
  - Atualizar etapa 4 da receita Colab com exportação e quantização reais via `optimum.onnxruntime` (`ORTModelForCausalLM.from_pretrained(..., export=True)` + `ORTQuantizer` / `AutoQuantizationConfig.avx512_vnni` / `arm64` ou `onnxruntime.quantization.quantize_dynamic`) gerando `models/model_int8.onnx`.

## Consequências
- **Positivas**: Eliminação de falsos positivos de avaliação (`eval`), fim de corrupção JSON no `stdout`, cache AST consistente, métricas estatísticas corretas, suporte real a TypeScript em Remotion e transparência absoluta nos motores System-One.
- **Riscos e Mitigações**: `test_metaprompt_engine.py:66` referencia `"cli.py"` e será atualizado junto ao refiner; `test_cli_decide_triage_output_file` espera `"Relatório salvo"` em `stdout` e será preservado.
