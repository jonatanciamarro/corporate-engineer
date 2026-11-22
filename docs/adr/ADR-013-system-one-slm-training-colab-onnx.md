# ADR-013: System-One SLM Fine-Tuning Pipeline, Google Colab Interactive Notebook & ONNX Int8 Runtime Loader

## Status
Aceito (Accepted)

## Data
2026-11-21

## Contexto & Motivação
No âmbito das melhorias IMP-0013 e IMP-0014, o framework `corporate-engineer` estabeleceu o motor de decisão rápida do Sistema 1, dotado de roteamento heurístico, decodificação restrita por autômatos finitos (Outlines) e uma interface preliminar de NLI (Natural Language Inference). Além disso, foi construído um gerador de datasets sintéticos que consolidou 100 amostras corporativas anotadas em `data/system_one_dataset.jsonl`.

Para viabilizar a conclusão da **Trilha 1 do Roadmap**, é indispensável:
1. Disponibilizar um fluxo de treinamento real e acessível sem custos de infraestrutura corporativa, aproveitando a GPU Nvidia T4 gratuita do Google Colab (VRAM < 1.5GB, tempo de execução estimado entre 5 a 8 minutos);
2. Entregar um **Jupyter Notebook interativo** (`notebooks/train_system_one_colab.ipynb`) com badge direta "Open in Colab", carregamento automático do dataset, fine-tuning com LoRA/PEFT (`Qwen/Qwen2.5-0.5B-Instruct`), exportação para ONNX e quantização dinâmica Int8 com download direto de `model_int8.onnx`;
3. Atualizar o script de console `scripts/train_system_one_colab.py` e o gerador `SystemOneTrainer` em `src/corporate_engineer/system_one/trainer.py` com o caminho real do dataset (`data/system_one_dataset.jsonl`) e rotinas ativas de SFTTrainer e exportação ONNX;
4. Implementar carregamento transparente (*lazy loading*) com fallback elegante no `ONNXNLIDecisionEngine` (`src/corporate_engineer/system_one/nli_engine.py`), capaz de utilizar o modelo quantizado `models/model_int8.onnx` quando presente e recair de forma transparente para o motor heurístico na ausência de GPU ou runtime ONNX.

## Decisão de Arquitetura

1. **Jupyter Notebook Interativo & Script Colab Atualizado**:
   - Criação de `notebooks/train_system_one_colab.ipynb` com células autônomas:
     - Instalação de dependências (`transformers`, `peft`, `trl`, `datasets`, `accelerate`, `onnx`, `onnxruntime`);
     - Leitura resiliente de `data/system_one_dataset.jsonl` (ou upload dinâmico no Colab via `files.upload()`);
     - Formatação ChatML / Qwen (`<|im_start|>system...<|im_end|>`);
     - Fine-Tuning via `SFTTrainer` com `LoraConfig` (r=16, lora_alpha=32, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], fp16=True);
     - Exportação ONNX e quantização dinâmica Int8 (`model_int8.onnx`);
     - Download automático em 1-clique para transferência direta para a pasta `models/` do projeto.
   - Atualização de `scripts/train_system_one_colab.py` e `SystemOneTrainer.generate_colab_recipe()` alinhando caminhos de arquivo e comandos ativos.

2. **Diretório e Estrutura de Modelos (`models/`)**:
   - Criação do diretório `models/` no root do projeto com arquivo `.gitkeep` e instrução no `.gitignore` para ignorar checkpoints intermediários pesados, preservando o artefato de modelo quantizado de referência ou mock.

3. **Runtime Loader com Lazy Loading & Graceful Fallback (`src/corporate_engineer/system_one/nli_engine.py`)**:
   - A classe `ONNXNLIDecisionEngine` adota verificação preguiçosa de `models/model_int8.onnx` ou caminho customizado via parâmetro/ambiente (`SYSTEM_ONE_ONNX_MODEL_PATH`).
   - Se `onnxruntime` estiver disponível e o arquivo de modelo existir, inicializa `onnxruntime.InferenceSession` com provedor CPU otimizado.
   - Caso o modelo ainda não tenha sido baixado ou `onnxruntime` não esteja instalado, a inferência é delegada com total fidelidade para o `HeuristicDecisionEngine`, mantendo a garantia de tempo de resposta sub-1ms sem interrupção de serviço.

4. **Modelos DTO Pydantic v2**:
   - Utilização de `DatasetReport`, `TrainingSample` e `SystemOneReport` já definidos em `src/corporate_engineer/models.py`.

## Consequências
- **Positivas**:
  - Custo zero de infraestrutura: treinamento executado no Google Colab T4 gratuito em ~5-8 minutos.
  - Portabilidade absoluta: modelo final quantizado Int8 possui tamanho reduzido (~350MB-500MB) e roda localmente em CPU com latência <10ms.
  - Zero atrito para desenvolvedores e pipelines CI/CD através do fallback transparente para o motor heurístico.
  - Totalmente testado via testes automatizados sem exigência de GPU no runner de testes.
- **Mitigações**:
  - Checkpoints intermediários do Hugging Face são excluídos após a quantização ONNX para não sobrecarregar disco.
  - O script e notebook possuem tratamento defensivo para ausência de GPU, permitindo execução de dry-run.
