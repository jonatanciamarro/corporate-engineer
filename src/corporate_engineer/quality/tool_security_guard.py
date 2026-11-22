"""
PreToolUse Zero-Secret Guard (IMP-0025).
Intercepts tool executions (write_file, edit_file, run_command) before they touch disk or shell
to prevent leakage of API keys, tokens, and private credentials.
"""

from __future__ import annotations

import re
from typing import Any

# 10 High-Confidence Secret Signatures
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Personal Access Token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b")),
    ("OpenAI API Key", re.compile(r"sk-(?:proj-|live-)?[a-zA-Z0-9]{32,}")),
    ("Anthropic API Key", re.compile(r"sk-ant-[a-zA-Z0-9]{32,}")),
    ("Google Gemini/Cloud API Key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9]{10,13}-[a-zA-Z0-9]{24,}")),
    ("Stripe API Key", re.compile(r"(?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}")),
    ("RSA/OpenSSH Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "Generic Hardcoded Secret",
        re.compile(
            r"""(?i)(?:api_key|secret_key|client_secret|db_password|access_token)\s*[:=]\s*["']([A-Za-z0-9_\-\.\$]{20,})["']"""
        ),
    ),
]

SAFE_PLACEHOLDERS = [
    "your_api_key",
    "<api_key>",
    "placeholder",
    "fake_",
    "dummy",
    "test_key",
    "test_api_key",
    "mock",
    "[REDACTED_SECRET]",
]


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

    for line in full_text.splitlines():
        line_lower = line.lower()
        if any(dummy in line_lower for dummy in SAFE_PLACEHOLDERS):
            continue

        for rule_name, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_str = match.group(0)
                masked = (
                    matched_str[:4] + "*" * (len(matched_str) - 8) + matched_str[-4:]
                    if len(matched_str) > 8
                    else "***"
                )
                return {
                    "decision": "deny",
                    "reason": (
                        f"Zero-Secret Guard: Bloqueada tentativa de escrita de credencial exposta "
                        f"({rule_name}: {masked}) na ferramenta `{tool_name}`. "
                        "Nunca persista credenciais ou tokens em código fonte!"
                    ),
                }

    return {"decision": "allow"}
