# Pull Request: feat(lora): Gemini LoRA modular pipeline for DarkFactory motion & tool-calling (IMP-0024)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0024`
- **Tipo de Alteração**: `feat`
- **Escopo**: `lora` / `models` / `cli`
- **ADR Associado**: [ADR-020: Gemini LoRA Modular Pipeline](../adr/ADR-020-gemini-lora-motion-and-tool-calling-pipeline.md)

---

## 🎯 Resumo das Modificações

Implementação do **Gemini LoRA Modular Pipeline (IMP-0024 / ADR-020)** para especialização do Gemini 3.8 Flash no projeto **DarkFactory**:

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `LoraDomain`: Enum tipado com `MOTION_REMOTION`, `MOTION_MANIM`, `MOTION_BLENDER` e `TOOL_CALLING`.
   - `LoraTrainingSample`: Contrato de dados com `id`, `domain`, `system_instruction`, `user_prompt`, `model_response` e `metadata`.
   - `LoraDatasetConfig`: Configuração com validação de limites de split (`train_split_ratio` entre 0.05 e 0.95), seleção de domínios, contagem de amostras e seed determinística.
   - `LoraValidationReport`: Relatório com contagens de amostras válidas/inválidas, aprovação booleana e lista de erros de sintaxe.
   - `LoraExportResult`: Relatório de exportação com contagens train/validation, caminhos dos arquivos JSONL, estimativa de tokens e contador de segredos sanitizados.

2. **Gerador de Datasets Sintéticos Especializados (`src/corporate_engineer/lora/generator.py`)**:
   - `LoraDatasetGenerator` gerando código com estética industrial da DarkFactory:
     - **Remotion**: Componentes React/TypeScript com `useCurrentFrame`, `interpolate` e curvas `spring` cinematográficas.
     - **Manim**: Cenas procedurais em Python com `Scene`, `FadeIn`, `Transform` e curvas de interpolação.
     - **Blender Python**: Scripts `bpy` com inserção procedural de keyframes, nós de material e iluminação volumétrica escura.
     - **Tool Calling**: Traces de execução multi-turn com chamadas e respostas de ferramentas em formato estruturado.

3. **Validador de Sintaxe & AST (`src/corporate_engineer/lora/validator.py`)**:
   - `LoraSyntaxValidator` com análise estática estrita:
     - Validação de AST Python via `ast.parse` para Manim e Blender.
     - Validação sintática e de tags balanceadas para Remotion TSX/JSX.
     - Validação estrita de JSON Schema para chamadas de ferramentas.
     - Geração de relatório consolidado em lote (`validate_batch`).

4. **Formatador & Exportador Vertex AI SFT (`src/corporate_engineer/lora/exporter.py`)**:
   - `LoraVertexExporter` exportando no formato oficial da Google Cloud Vertex AI / AI Studio (`train.jsonl` e `validation.jsonl`):
     - `{"contents": [{"role": "user", ...}, {"role": "model", ...}]}`
   - **Zero-Secret Guard**: Sanitização automática de credenciais e chaves simuladas (`[REDACTED_SECRET]`).
   - Particionamento determinístico de dados com seed configurável.
   - Estimativa antecipada de tokens para planejamento de custos de treinamento.

5. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer lora`:
     - `generate`: gera datasets sintéticos nos domínios desejados com `--domains`, `--samples`, `--seed`, `--output`.
     - `validate`: valida integridade sintática e de schemas de datasets com `--input`, `--format [text|json]`.
     - `export`: particiona e exporta para o formato Vertex AI com `--input`, `--output-dir`, `--split`, `--no-sanitize`.

6. **Suíte de Testes Automatizados (Shift-Left TDD)**:
   - 29 novos testes em `tests/test_gemini_lora_pipeline.py` (100% PASS).
   - Expansão da suíte global para **219 testes automatizados** (0 falhas, 0 regressões).

---

## 🧪 Evidências de Teste & Qualidade

```text
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.2.0, pluggy-1.7.0
plugins: hypothesis-6.168.5, cov-7.1.0
collected 219 items

tests\test_gemini_lora_pipeline.py .............................         [ 13%]
... (219 passed in 21.06s - 100% de sucesso)

Ruff Linter: All checks passed! (0 erros)
Ruff Formatter: 118 files already formatted (0 problemas de estilo)
Mypy Strict Type Check: Success: no issues found in 69 source files (0 erros de tipagem)
Pre-Flight Secret Scanner: PASS (0 segredos ou credenciais expostas)
```
