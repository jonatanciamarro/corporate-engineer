"""
Syntax and AST validation engine for Gemini LoRA DarkFactory datasets.
"""

import ast
import json
import re
from typing import Any

from corporate_engineer.models import LoraDomain, LoraTrainingSample, LoraValidationReport


class LoraSyntaxValidator:
    """Validates syntax and AST integrity for multi-domain LoRA training samples."""

    def validate_python_ast(self, code: str) -> tuple[bool, list[str]]:
        """Validates Python code by parsing it into an AST."""
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as exc:
            return False, [f"SyntaxError: {exc.msg} at line {exc.lineno}"]
        except Exception as exc:  # noqa: BLE001
            return False, [f"SyntaxError: {exc}"]

    def _strip_strings_and_comments(self, code: str) -> str:
        """Strips string literals and comments to assist balanced bracket and JSX inspection."""
        chars: list[str] = []
        i = 0
        n = len(code)

        while i < n:
            # Single-line comment
            if code[i : i + 2] == "//":
                while i < n and code[i] != "\n":
                    chars.append(" ")
                    i += 1
                continue

            # Multi-line comment
            if code[i : i + 2] == "/*":
                i += 2
                while i < n and code[i : i + 2] != "*/":
                    chars.append(" ")
                    i += 1
                i = min(n, i + 2)
                continue

            # String literal: single, double quote or backtick
            if code[i] in ("'", '"', "`"):
                quote = code[i]
                chars.append(" ")
                i += 1
                while i < n:
                    if code[i] == "\\":
                        i += 2
                        chars.extend([" ", " "])
                        continue
                    if code[i] == quote:
                        chars.append(" ")
                        i += 1
                        break
                    chars.append(" ")
                    i += 1
                continue

            chars.append(code[i])
            i += 1

        return "".join(chars)

    def validate_remotion_syntax(self, code: str) -> tuple[bool, list[str]]:
        """Validates TypeScript / React JSX motion syntax for Remotion components."""
        stripped = self._strip_strings_and_comments(code)
        errors: list[str] = []

        # 1. Bracket balancing check
        bracket_pairs = {")": "(", "}": "{", "]": "["}
        stack: list[str] = []

        for ch in stripped:
            if ch in "({[":
                stack.append(ch)
            elif ch in ")}]":
                if not stack or stack[-1] != bracket_pairs[ch]:
                    errors.append(f"Unbalanced bracket: mismatched '{ch}'")
                    return False, errors
                stack.pop()

        if stack:
            errors.append(f"Unclosed bracket: '{stack[-1]}'")
            return False, errors

        # 2. JSX Tag balancing check
        tag_pattern = re.compile(r"<(/)?([a-zA-Z][a-zA-Z0-9_\.]*)\b([^>]*)>")
        tag_stack: list[str] = []

        for match in tag_pattern.finditer(stripped):
            is_closing = bool(match.group(1))
            tag_name = match.group(2)
            attrs = match.group(3).strip()

            # Skip self-closing tags (ending with /) or void HTML elements
            if (
                attrs.endswith("/") or tag_name.lower() in ("img", "br", "hr", "input")
            ) and not is_closing:
                continue

            if is_closing:
                if not tag_stack:
                    errors.append(f"Unexpected closing tag </{tag_name}>")
                    return False, errors
                expected_tag = tag_stack.pop()
                if expected_tag != tag_name:
                    errors.append(
                        f"Mismatched JSX tag: expected </{expected_tag}>, found </{tag_name}>"
                    )
                    return False, errors
            else:
                tag_stack.append(tag_name)

        if tag_stack:
            errors.append(f"Unclosed JSX tag <{tag_stack[-1]}>")
            return False, errors

        return True, []

    def validate_tool_call_schema(self, payload: str) -> tuple[bool, list[str]]:
        """Validates structured JSON function calling schema for tool-use samples."""
        try:
            data: Any = json.loads(payload)
        except Exception as exc:  # noqa: BLE001
            return False, [f"JSONDecodeError: {exc}"]

        if not isinstance(data, dict):
            return False, ["Tool call payload must be a JSON object"]

        has_tool_field = any(k in data for k in ("name", "tool", "tool_calls", "function"))
        if not has_tool_field:
            return False, ["Tool call payload missing required 'name' or 'tool' field"]

        return True, []

    def validate_sample(self, sample: LoraTrainingSample) -> tuple[bool, list[str]]:
        """Dispatches sample validation based on domain and updates sample state."""
        if sample.domain == LoraDomain.MOTION_REMOTION:
            is_valid, errors = self.validate_remotion_syntax(sample.target_response)
        elif sample.domain in (LoraDomain.MOTION_MANIM, LoraDomain.MOTION_BLENDER):
            is_valid, errors = self.validate_python_ast(sample.target_response)
        elif sample.domain == LoraDomain.TOOL_CALLING:
            is_valid, errors = self.validate_tool_call_schema(sample.target_response)
        else:
            is_valid, errors = True, []

        sample.is_valid = is_valid
        sample.syntax_errors = errors
        return is_valid, errors

    def validate_batch(self, samples: list[LoraTrainingSample]) -> LoraValidationReport:
        """Validates a collection of samples and produces a consolidated report."""
        total = len(samples)
        valid = 0
        invalid = 0
        domain_breakdown: dict[str, int] = {}
        all_errors: list[str] = []

        for s in samples:
            dom_key = s.domain.value if hasattr(s.domain, "value") else str(s.domain)
            domain_breakdown[dom_key] = domain_breakdown.get(dom_key, 0) + 1
            ok, errs = self.validate_sample(s)
            if ok:
                valid += 1
            else:
                invalid += 1
                all_errors.extend([f"[{s.id}] {e}" for e in errs])

        return LoraValidationReport(
            total_samples=total,
            valid_samples=valid,
            invalid_samples=invalid,
            domain_breakdown=domain_breakdown,
            errors=all_errors,
            is_approved=(invalid == 0),
        )
