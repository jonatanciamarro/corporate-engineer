#!/usr/bin/env python3
"""
secret_scanner.py - Pre-Flight Security & Secret Audit Scanner for Corporate Pipelines.
Scans files in git repository or specified path for exposed credentials, API keys,
private keys, and tokens, returning exit code 0 if clean, or exit code 1 with findings.
Reuses CanonicalSecretScanner (IMP-0027 / ADR-025).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

# Try importing CanonicalSecretScanner from corporate_engineer package
try:
    from corporate_engineer.quality.secret_scanner import (
        IGNORE_DIRS,
        IGNORE_EXTENSIONS,
        SAFE_PLACEHOLDERS,
        SECRET_PATTERNS,
        CanonicalSecretScanner,
    )
except ImportError:
    # Add repo root and src/ to sys.path to allow importing from corporate_engineer
    repo_root = Path(__file__).resolve().parents[4]
    src_dir = repo_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    try:
        from corporate_engineer.quality.secret_scanner import (
            IGNORE_DIRS,
            IGNORE_EXTENSIONS,
            SAFE_PLACEHOLDERS,
            SECRET_PATTERNS,
            CanonicalSecretScanner,
        )
    except ImportError:
        # Fallback patterns if completely outside package environment
        SECRET_PATTERNS = [
            ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
            (
                "AWS Access Key ID",
                re.compile(
                    r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16,}\b"
                ),
            ),
            (
                "GitHub Personal Access Token",
                re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
            ),
            ("GitLab Personal Access Token", re.compile(r"\bglpat-[0-9a-zA-Z_\-]{20,}\b")),
            (
                "OpenAI API Key",
                re.compile(r"\bsk-(?!ant-)(?:proj-|svcacct-|live-)?[A-Za-z0-9_\-]{32,}\b"),
            ),
            (
                "Anthropic API Key",
                re.compile(r"\bsk-ant-(?:api\d{2}-)?[A-Za-z0-9_\-]{32,}\b"),
            ),
            ("Google Gemini/Cloud API Key", re.compile(r"\bAIzaSy[A-Za-z0-9_\-]{33}\b")),
            ("Slack Token", re.compile(r"\bxox[baprs]-[0-9]{10,13}-[a-zA-Z0-9]{24,}\b")),
            ("Stripe API Key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}\b")),
            (
                "Generic Hardcoded Secret",
                re.compile(
                    r"""(?i)(?:api_key|secret_key|client_secret|db_password|access_token)\s*[:=]\s*["']([A-Za-z0-9_\-\.\$]{16,})["']"""
                ),
            ),
        ]

        SAFE_PLACEHOLDERS = [
            "your_api_key",
            "example_key",
            "your_example",
            "<api_key>",
            "placeholder",
            "fake_",
            "xxx",
            "dummy",
            "test_key",
            "test_api_key",
            "mock",
            "[REDACTED_SECRET]",
        ]

        IGNORE_DIRS = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            "target",
            "bin",
            "obj",
            ".idea",
            ".vscode",
            "chrome_session",
            "data",
            "models",
        }

        IGNORE_EXTENSIONS = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".pyc",
            ".lock",
            ".svg",
            ".woff",
            ".woff2",
            ".onnx",
            ".bin",
            ".gguf",
        }

        class CanonicalSecretScanner:  # type: ignore[no-redef]
            def __init__(
                self,
                patterns: list[tuple[str, re.Pattern[str]]] | None = None,
                safe_placeholders: list[str] | None = None,
                ignore_dirs: set[str] | None = None,
                ignore_extensions: set[str] | None = None,
            ) -> None:
                self.patterns = patterns or SECRET_PATTERNS
                self.safe_placeholders = safe_placeholders or SAFE_PLACEHOLDERS
                self.ignore_dirs = set(ignore_dirs) if ignore_dirs is not None else set(IGNORE_DIRS)
                self.ignore_extensions = (
                    set(ignore_extensions)
                    if ignore_extensions is not None
                    else set(IGNORE_EXTENSIONS)
                )

            def is_safe_line(self, line: str) -> bool:
                lowered = line.lower()
                return any(p in lowered for p in self.safe_placeholders)

            def mask_secret(self, raw_secret: str) -> str:
                if len(raw_secret) > 8:
                    return raw_secret[:4] + "*" * (len(raw_secret) - 8) + raw_secret[-4:]
                return "***"

            def scan_text(self, text: str, source_identifier: str = "") -> list[dict[str, Any]]:
                findings: list[dict[str, Any]] = []
                for line_num, line in enumerate(text.splitlines(), start=1):
                    if self.is_safe_line(line):
                        continue
                    for rule_name, pattern in self.patterns:
                        match = pattern.search(line)
                        if match:
                            matched_str = match.group(0)
                            findings.append(
                                {
                                    "file": source_identifier,
                                    "line": line_num,
                                    "rule_name": rule_name,
                                    "type": rule_name,
                                    "masked_secret": self.mask_secret(matched_str),
                                }
                            )
                            break
                return findings

            def scan_file(
                self,
                file_path: Path | str,
                ignore_extensions: set[str] | None = None,
            ) -> list[dict[str, Any]]:
                path_obj = Path(file_path)
                skip_exts = (
                    self.ignore_extensions if ignore_extensions is None else ignore_extensions
                )
                if path_obj.suffix.lower() in skip_exts:
                    return []
                try:
                    content = path_obj.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    return []
                return self.scan_text(content, source_identifier=str(path_obj))

            def scan_directory(
                self,
                root_dir: Path | str,
                ignore_dirs: set[str] | None = None,
                ignore_extensions: set[str] | None = None,
            ) -> list[dict[str, Any]]:
                all_findings: list[dict[str, Any]] = []
                skip_dirs = self.ignore_dirs if ignore_dirs is None else ignore_dirs
                skip_exts = (
                    self.ignore_extensions if ignore_extensions is None else ignore_extensions
                )

                root_path = Path(root_dir).resolve()
                for root, dirs, files in os.walk(root_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]
                    rel_root = Path(root).relative_to(root_path)
                    if any(part.startswith(".") or part in skip_dirs for part in rel_root.parts):
                        continue

                    for filename in files:
                        ext = Path(filename).suffix.lower()
                        if ext in skip_exts:
                            continue
                        file_path = Path(root) / filename
                        findings = self.scan_file(file_path, ignore_extensions=skip_exts)
                        for f in findings:
                            f["file"] = str(file_path.relative_to(root_path)).replace("\\", "/")
                            all_findings.append(f)
                return all_findings


def scan_file(file_path: Path) -> list[tuple[str, int, str]]:
    """Scan a single file for credentials using CanonicalSecretScanner."""
    scanner = CanonicalSecretScanner()
    findings = scanner.scan_file(file_path)
    return [(f["rule_name"], f["line"], f["masked_secret"]) for f in findings]


def scan_directory(target_dir: Path) -> dict[str, list[tuple[str, int, str]]]:
    """Recursively scan directory for credentials using CanonicalSecretScanner."""
    scanner = CanonicalSecretScanner()
    raw_findings = scanner.scan_directory(target_dir)
    all_findings: dict[str, list[tuple[str, int, str]]] = {}
    for f in raw_findings:
        file_key = f["file"]
        if file_key not in all_findings:
            all_findings[file_key] = []
        all_findings[file_key].append((f["rule_name"], f["line"], f["masked_secret"]))
    return all_findings


def main() -> None:
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(f"🔒 Executando Corporate Pre-Flight Secret Scanner em: {target_dir.resolve()} ...")

    findings = scan_directory(target_dir)

    if not findings:
        print("✅ Pre-Flight Secret Scan PASS: Nenhum segredo ou credencial exposta foi detectada.")
        sys.exit(0)
    else:
        print("\n❌ 🔴 CRITICAL: Segredos detectados nos seguintes arquivos:")
        for file_path, items in findings.items():
            print(f"\n📄 {file_path}:")
            for rule_name, line_num, masked in items:
                print(f"   [Linha {line_num}] Tipo: {rule_name} | Valor mascarado: {masked}")

        print(
            "\n🚫 Interrompendo pipeline: remova as credenciais hardcoded antes de prosseguir para o Gate 2."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
