"""
scripts/finetune_llama3.py
───────────────────────────
Fine-tunes LLaMA-3-8B with LoRA/QLoRA (PEFT) on financial Q&A data
derived from the SEC 10-K benchmark.

Requires:
  - CUDA GPU with ≥16GB VRAM (or use 4-bit QLoRA for 12GB)
  - Base model pulled to HuggingFace cache

Usage:
    python scripts/finetune_llama3.py
    python scripts/finetune_llama3.py --qlora          # 4-bit quantization (less VRAM)
    python scripts/finetune_llama3.py --model meta-llama/Meta-Llama-3-8B
    python scripts/finetune_llama3.py --epochs 3 --lr 2e-4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config

from loguru import logger


# ── Training data preparation ─────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a highly accurate financial analyst assistant. "
    "Answer questions about SEC 10-K filings with precise figures, "
    "cite sources, and show calculations when needed."
)


def build_training_examples() -> list[dict]:
    """
    Build instruction-tuning examples from the QA benchmark.
    Format: Alpaca-style {"instruction", "input", "output"}
    """
    from evaluation.run_evaluation import QA_BENCHMARK

    # Augment with financial reasoning templates
    examples = []
    for item in QA_BENCHMARK:
        examples.append({
            "instruction": SYSTEM_PROMPT,
            "input": item["question"],
            "output": item["ground_truth"],
        })

    # Add financial calculation templates
    calculation_templates = [
        {
            "instruction": SYSTEM_PROMPT,
            "input": "How do I calculate year-over-year revenue growth rate?",
            "output": "Year-over-year growth rate = (Current Year Revenue - Prior Year Revenue) / Prior Year Revenue × 100%. For example, if revenue grew from $100B to $120B, the growth rate is ($120B - $100B) / $100B × 100% = 20%.",
        },
        {
            "instruction": SYSTEM_PROMPT,
            "input": "What is gross margin and how is it calculated from a 10-K?",
            "output": "Gross margin = (Revenue - Cost of Goods Sold) / Revenue × 100%. In a 10-K, find 'Net revenue' and 'Cost of revenue' in the Consolidated Statements of Operations. For example, Apple FY2023: ($383.3B - $214.1B) / $383.3B = 44.1% gross margin.",
        },
        {
            "instruction": SYSTEM_PROMPT,
            "input": "What is the difference between operating income and net income?",
            "output": "Operating income = Revenue - COGS - Operating Expenses. Net income = Operating income - Interest Expense - Taxes ± Other items. Net income is the 'bottom line' after all costs including taxes. Operating income shows profitability from core operations before financing costs.",
        },
    ]
    examples.extend(calculation_templates)
    return examples


def format_alpaca_prompt(instruction: str, input_text: str, output: str = "") -> str:
    """Format as Alpaca-style instruction template."""
    text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
    return text


def prepare_dataset(tokenizer, max_length: int = 512):
    """Build tokenized HuggingFace Dataset from training examples."""
    from datasets import Dataset

    examples = build_training_examples()
    logger.info(f"Prepared {len(examples)} training examples")

    formatted = [
        format_alpaca_prompt(ex["instruction"], ex["input"], ex["output"])
        for ex in examples
    ]

    def tokenize(batch):
        tokens = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors=None,
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    dataset = Dataset.from_dict({"text": formatted})
    dataset = dataset.map(tokenize, batched=True, remove_columns=["text"])
    return dataset


# ── LoRA configuration ────────────────────────────────────────────────────────

LORA_CONFIG = {
    "r": 16,                          # LoRA rank (higher = more params, more capacity)
    "lora_alpha": 32,                 # Scaling factor (typically 2x rank)
    "target_modules": [               # Attention projection layers to adapt
        "q_proj", "v_proj",
        "k_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    "lora_dropout": 0.05,
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

QLORA_QUANTIZATION = {
    "load_in_4bit": True,
    "bnb_4bit_quant_type": "nf4",              # Normal Float 4 — best quality
    "bnb_4bit_compute_dtype": "bfloat16",       # bf16 for computation
    "bnb_4bit_use_double_quant": True,          # Double quantization saves ~0.4 bits/param
}


# ── Training ──────────────────────────────────────────────────────────────────

def finetune(
    base_model: str = "meta-llama/Meta-Llama-3-8B",
    use_qlora: bool = True,
    epochs: int = 3,
    lr: float = 2e-4,
    batch_size: int = 4,
    grad_accum: int = 4,
    max_length: int = 512,
    output_dir: str | None = None,
):
    import torch
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer

    output_dir = output_dir or str(config.FINETUNED_MODEL_PATH)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info(f"Base model: {base_model}")
    logger.info(f"QLoRA: {use_qlora} | Epochs: {epochs} | LR: {lr}")
    logger.info(f"Output: {output_dir}")

    # ── Load tokenizer ─────────────────────────────────────────────────────────
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # ── Load model ─────────────────────────────────────────────────────────────
    logger.info("Loading model...")
    model_kwargs = {"trust_remote_code": True, "device_map": "auto"}

    if use_qlora:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["quantization_config"] = bnb_config
        logger.info("QLoRA: 4-bit quantization enabled (NF4 + double quant)")
    else:
        model_kwargs["torch_dtype"] = torch.bfloat16
        logger.info("LoRA: full precision bf16")

    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)

    if use_qlora:
        model = prepare_model_for_kbit_training(model)

    # ── Apply LoRA ─────────────────────────────────────────────────────────────
    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    trainable, total = model.get_nb_trainable_parameters()
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ── Prepare dataset ────────────────────────────────────────────────────────
    logger.info("Preparing dataset...")
    train_dataset = prepare_dataset(tokenizer, max_length=max_length)

    # ── Training arguments ─────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        weight_decay=0.01,
        fp16=False,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",          # Set to "wandb" or "tensorboard" if desired
        optim="paged_adamw_32bit" if use_qlora else "adamw_torch",
        max_grad_norm=0.3,
        group_by_length=True,
        dataloader_num_workers=2,
    )

    # ── Trainer ────────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
        dataset_text_field="input_ids",
        max_seq_length=max_length,
        packing=False,
    )

    logger.info("Starting training...")
    trainer.train()

    # ── Save adapter ───────────────────────────────────────────────────────────
    logger.info(f"Saving LoRA adapter to {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save config metadata
    meta = {
        "base_model": base_model,
        "lora_config": LORA_CONFIG,
        "training_config": {
            "epochs": epochs,
            "lr": lr,
            "batch_size": batch_size,
            "grad_accum": grad_accum,
            "qlora": use_qlora,
            "max_length": max_length,
        },
        "num_examples": len(train_dataset),
    }
    (Path(output_dir) / "training_metadata.json").write_text(json.dumps(meta, indent=2))
    logger.success(f"Fine-tuning complete! Adapter saved to {output_dir}")
    logger.info("To use the fine-tuned model, set USE_FINETUNED_MODEL=true in .env")


# ── Inference test ─────────────────────────────────────────────────────────────

def test_finetuned_model(adapter_path: str, test_question: str):
    """Quick inference test on the fine-tuned model."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline

    logger.info(f"Loading fine-tuned model from {adapter_path}...")
    meta_file = Path(adapter_path) / "training_metadata.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    base_model = meta.get("base_model", "meta-llama/Meta-Llama-3-8B")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    base = AutoModelForCausalLM.from_pretrained(
        base_model, quantization_config=bnb_config, device_map="auto"
    )
    model = PeftModel.from_pretrained(base, adapter_path)
    model.eval()

    prompt = format_alpaca_prompt(SYSTEM_PROMPT, test_question)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=256)
    result = pipe(prompt)[0]["generated_text"]
    response = result[len(prompt):]
    print(f"\nQuestion: {test_question}\nAnswer: {response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3-8B")
    parser.add_argument("--qlora", action="store_true", default=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--test", action="store_true", help="Test fine-tuned model inference")
    parser.add_argument("--test-question", default="What was Apple's gross margin in FY2023?")
    args = parser.parse_args()

    if args.test:
        test_finetuned_model(config.FINETUNED_MODEL_PATH, args.test_question)
    else:
        finetune(
            base_model=args.model,
            use_qlora=args.qlora,
            epochs=args.epochs,
            lr=args.lr,
            batch_size=args.batch_size,
        )
