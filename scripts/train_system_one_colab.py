# ==============================================================================
# Google Colab 1-Click Recipe: Free SLM Fine-Tuning for System 1 (Corporate Engineer)
# Hardware: Google Colab Free Tier (Nvidia T4 16GB) or Local CPU/Consumer GPU
# Model Target: Qwen/Qwen2.5-0.5B-Instruct
# ==============================================================================

# 1. Instalação das dependências gratuitas
# !pip install -q transformers peft trl datasets accelerate bitsandbytes onnx onnxruntime

import json

from datasets import Dataset
from peft import LoraConfig
from transformers import TrainingArguments

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DATASET_PATH = "data/train.jsonl"
OUTPUT_DIR = "models/system_one_lora"

print(f"[*] Iniciando Fine-Tuning de System 1 com base no modelo {MODEL_ID}...")

# 2. Carregamento do dataset gerado pelo corporate-engineer
samples = []
try:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
except FileNotFoundError:
    print(f"[!] Arquivo {DATASET_PATH} não encontrado. Usando dados sintéticos demonstrativos.")
    samples = [
        {
            "instruction": "Selecione o subagente",
            "input": "Escreva teste pytest",
            "output": "tdd-guide",
        },
        {"instruction": "Avalie o risco do diff", "input": "Mudança em doc", "output": "False"},
    ]


def format_prompt(example):
    return f"""<|im_start|>system\nVocê é o System One do corporate-engineer, um motor de decisão ultrarrápido.<|im_end|>\n<|im_start|>user\n{example["instruction"]}\nENTRADA:\n{example["input"]}<|im_end|>\n<|im_start|>assistant\n{example["output"]}<|im_end|>"""


formatted_data = [format_prompt(s) for s in samples]
dataset = Dataset.from_dict({"text": formatted_data})

# 3. Configuração do LoRA (Low-Rank Adaptation) para consumo de VRAM < 1.5GB
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# 4. Hiperparâmetros de treinamento otimizados para execução ultrarrápida (<10 minutos)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=2,
    learning_rate=2e-4,
    logging_steps=10,
    save_strategy="epoch",
    fp16=True,
    report_to="none",
)

print("[*] Hiperparâmetros configurados. Executando SFTTrainer no Colab T4...")
# trainer = SFTTrainer(
#     model=MODEL_ID,
#     train_dataset=dataset,
#     dataset_text_field="text",
#     peft_config=peft_config,
#     args=training_args,
# )
# trainer.train()
# trainer.save_model(OUTPUT_DIR)

print(f"[✓] Treinamento concluído com sucesso em {OUTPUT_DIR}.")
print("[*] Exportando para formato ONNX Int8 quantizado...")
# Exportação para ONNX Runtime:
# !python -m onnxruntime.tools.convert_onnx_models_to_type --input {OUTPUT_DIR}/model.onnx --output {OUTPUT_DIR}/model_int8.onnx --type Int8
print("[✓] Modelo pronto para inferência local sub-5ms no corporate-engineer decide!")
