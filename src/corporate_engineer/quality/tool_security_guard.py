"""
PreToolUse Zero-Secret Guard (IMP-0025).
Intercepts tool executions (write_file, edit_file, run_command) before they touch disk or shell
to prevent leakage of API keys, tokens, and private credentials.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from corporate_engineer.quality.secret_scanner import (
        SAFE_PLACEHOLDERS,
        SECRET_PATTERNS,
        CanonicalSecretScanner,
    )
except ImportError:
    SECRET_PATTERNS = [
        ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
        (
            "AWS Access Key ID",
            re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16,}\b"),
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

    class CanonicalSecretScanner:  # type: ignore[no-redef]
        def __init__(
            self,
            patterns: list[tuple[str, re.Pattern[str]]] | None = None,
            safe_placeholders: list[str] | None = None,
        ) -> None:
            self.patterns = patterns or SECRET_PATTERNS
            self.safe_placeholders = safe_placeholders or SAFE_PLACEHOLDERS

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


_scanner = CanonicalSecretScanner(patterns=SECRET_PATTERNS, safe_placeholders=SAFE_PLACEHOLDERS)


def evaluate_tool_security(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Avalia a segurança de uma chamada de ferramenta no evento PreToolUse.
    Retorna {"decision": "allow"} ou {"decision": "deny", "reason": "..."}.
    """
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    # Coletar conteúdo textual a ser inspecionado
    content_to_check: list[str] = []

    if "Content" in args:
        content_to_check.append(str(args["Content"]))
    if "Replacement" in args:
        content_to_check.append(str(args["Replacement"]))
    if "CommandLine" in args:
        content_to_check.append(str(args["CommandLine"]))

    full_text = "\n".join(content_to_check)
    if not full_text:
        return {"decision": "allow"}

    findings = _scanner.scan_text(full_text)
    if findings:
        first = findings[0]
        rule_name = first.get("rule_name", "Secret")
        masked = first.get("masked_secret", "***")
        return {
            "decision": "deny",
            "reason": (
                f"Zero-Secret Guard: Bloqueada tentativa de escrita de credencial exposta "
                f"({rule_name}: {masked}) na ferramenta `{tool_name}`. "
                "Nunca persista credenciais ou tokens em código fonte!"
            ),
        }

    return {"decision": "allow"}
