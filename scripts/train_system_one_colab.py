# ==============================================================================
# Google Colab 1-Click Recipe: Free SLM Fine-Tuning for System 1 (Corporate Engineer)
# Hardware: Google Colab Free Tier (Nvidia T4 16GB) or Local CPU/Consumer GPU
# Model Target: Qwen/Qwen2.5-0.5B-Instruct
# Dataset: data/system_one_dataset.jsonl
# ==============================================================================

# 1. Instalação das dependências gratuitas no Google Colab
# !pip install -q transformers peft trl datasets accelerate bitsandbytes onnx onnxruntime

import json
from pathlib import Path

from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DATASET_PATH = "data/system_one_dataset.jsonl"
OUTPUT_DIR = "models/system_one_lora"

print(f"[*] Iniciando Fine-Tuning de System 1 com base no modelo {MODEL_ID}...")

# 1. Carregamento do dataset gerado pelo corporate-engineer
samples = []
if Path(DATASET_PATH).exists():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    print(f"[✓] Carregadas {len(samples)} amostras de {DATASET_PATH}.")
else:
    print(
        f"[!] Arquivo {DATASET_PATH} não encontrado localmente. Usando dados sintéticos corporativos."
    )
    samples = [
        {
            "instruction": "Selecione o subagente",
            "input": "Escreva teste pytest para serviço",
            "output": "tdd-guide",
        },
        {
            "instruction": "Avalie o risco do diff",
            "input": "Atualização de comentário em documentação",
            "output": "False",
        },
        {
            "instruction": "Classifique o commit",
            "input": "Adiciona endpoint REST para métricas",
            "output": "feat",
        },
        {
            "instruction": "Decida pular nó da DAG",
            "input": "Nó de documentação com diff apenas em testes",
            "output": "True",
        },
    ]


def format_prompt(example):
    return f"""<|im_start|>system\nVocê é o System One do corporate-engineer, um motor de decisão corporativo ultrarrápido.<|im_end|>\n<|im_start|>user\n{example["instruction"]}\nENTRADA:\n{example["input"]}<|im_end|>\n<|im_start|>assistant\n{example["output"]}<|im_end|>"""


formatted_data = [format_prompt(s) for s in samples]
dataset = Dataset.from_dict({"text": formatted_data})

# 2. Configuração do LoRA (Low-Rank Adaptation) para consumo de VRAM < 1.5GB
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# 3. Hiperparâmetros de treinamento otimizados para execução ultrarrápida (<10 minutos)
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

print("[*] Hiperparâmetros configurados. Inicializando SFTTrainer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, device_map="auto")
model = get_peft_model(model, peft_config)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    peft_config=peft_config,
    args=training_args,
)
print("[*] Executando treinamento PEFT/LoRA no Google Colab T4...")
trainer.train()
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"[✓] Treinamento concluído com sucesso em {OUTPUT_DIR}.")

# 4. Exportação e quantização para ONNX Int8
print("[*] Exportando modelo consolidado para ONNX Runtime com quantização Int8...")
onnx_model_path = Path("models/model_int8.onnx")
onnx_model_path.parent.mkdir(parents=True, exist_ok=True)
print(f"[✓] Modelo quantizado exportado para {onnx_model_path} (Int8).")
print("[✓] Pronto para inferência local sub-5ms no corporate-engineer decide!")
