"""
Vertex AI JSONL dataset exporter for Gemini LoRA DarkFactory fine-tuning (ADR-020).
"""

import json
import math
import re
from pathlib import Path
from typing import Any

from corporate_engineer.models import LoraDatasetConfig, LoraExportResult, LoraTrainingSample

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Za-z]{16,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"ghp_[0-9A-Za-z]{36}"),
    re.compile(r"sk-[0-9A-Za-z]{20,}"),
]


class LoraVertexExporter:
    """Exports validated LoRA samples into Vertex AI JSONL Supervised Fine-Tuning (SFT) formats."""

    def format_vertex_entry(self, sample: LoraTrainingSample) -> dict[str, Any]:
        """Formats a training sample into Vertex AI Gemini SFT schema."""
        entry: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": sample.user_prompt}],
                },
                {
                    "role": "model",
                    "parts": [{"text": sample.target_response}],
                },
            ]
        }
        if sample.system_instruction:
            entry["systemInstruction"] = {
                "role": "system",
                "parts": [{"text": sample.system_instruction}],
            }
        return entry

    def estimate_tokens(self, text: str) -> int:
        """Estimates token count using standard 4-characters-per-token heuristic."""
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 4))

    def sanitize_text(self, text: str) -> tuple[str, int]:
        """Scrubs hardcoded credentials and secrets, replacing with [REDACTED_SECRET]."""
        sanitized = text
        total_redacted = 0
        for pattern in SECRET_PATTERNS:
            sanitized, count = pattern.subn("[REDACTED_SECRET]", sanitized)
            total_redacted += count
        return sanitized, total_redacted

    def export_dataset(
        self,
        samples: list[LoraTrainingSample],
        output_dir: Path | str,
        config: LoraDatasetConfig | None = None,
    ) -> LoraExportResult:
        """Exports dataset into train.jsonl and validation.jsonl with deterministic splitting."""
        cfg = config or LoraDatasetConfig()
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        sanitized_secrets_count = 0
        prepared_samples: list[LoraTrainingSample] = []

        for s in samples:
            if cfg.sanitize_secrets:
                clean_sys, c1 = self.sanitize_text(s.system_instruction)
                clean_prompt, c2 = self.sanitize_text(s.user_prompt)
                clean_resp, c3 = self.sanitize_text(s.target_response)
                sanitized_secrets_count += c1 + c2 + c3
                prepared_samples.append(
                    LoraTrainingSample(
                        id=s.id,
                        domain=s.domain,
                        system_instruction=clean_sys,
                        user_prompt=clean_prompt,
                        target_response=clean_resp,
                        metadata=s.metadata,
                        is_valid=s.is_valid,
                        syntax_errors=s.syntax_errors,
                    )
                )
            else:
                prepared_samples.append(s)

        total_samples = len(prepared_samples)
        if total_samples <= 1:
            train_samples = prepared_samples
            val_samples: list[LoraTrainingSample] = []
        else:
            train_count = int(total_samples * cfg.train_split_ratio)
            train_samples = prepared_samples[:train_count]
            val_samples = prepared_samples[train_count:]

        train_file = out_path / "train.jsonl"
        val_file = out_path / "validation.jsonl"

        estimated_tokens = 0

        with open(train_file, "w", encoding="utf-8") as f:
            for s in train_samples:
                entry = self.format_vertex_entry(s)
                f.write(json.dumps(entry) + "\n")
                estimated_tokens += self.estimate_tokens(
                    s.system_instruction + s.user_prompt + s.target_response
                )

        with open(val_file, "w", encoding="utf-8") as f:
            for s in val_samples:
                entry = self.format_vertex_entry(s)
                f.write(json.dumps(entry) + "\n")
                estimated_tokens += self.estimate_tokens(
                    s.system_instruction + s.user_prompt + s.target_response
                )

        return LoraExportResult(
            train_file=str(train_file),
            validation_file=str(val_file),
            train_count=len(train_samples),
            validation_count=len(val_samples),
            estimated_tokens=estimated_tokens,
            success=True,
            sanitized_secrets_count=sanitized_secrets_count,
        )
