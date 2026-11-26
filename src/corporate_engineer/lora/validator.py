"""
Syntax and AST validation engine for Gemini LoRA DarkFactory datasets.
"""

import ast
import json
import re
from typing import Any

from corporate_engineer.models import LoraDomain, LoraTrainingSample, LoraValidationReport

_JSX_CLOSE_TAG_RE = re.compile(r"</([a-zA-Z][a-zA-Z0-9_.]*)\s*>")
_JSX_TAG_NAME_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_.]*")
_JSX_EXTENDS_RE = re.compile(r"^\s+extends\b")
_JSX_DEFAULT_TYPE_PARAM_RE = re.compile(r"^\s*=\s*[A-Za-z_{\[(]")
_JSX_VOID_ELEMENTS = frozenset({"img", "br", "hr", "input"})
_JSX_PRECEDING_KEYWORDS = frozenset(
    {
        "return",
        "yield",
        "await",
        "throw",
        "case",
        "else",
        "typeof",
        "void",
        "delete",
        "export",
        "default",
        "in",
        "of",
    }
)


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

    def _is_preceded_by_non_jsx_token(self, stripped: str, idx: int) -> bool:
        """Returns True when '<' at idx is immediately preceded on the same line by a value/type token."""
        k = idx - 1
        while k >= 0 and stripped[k] in (" ", "\t"):
            k -= 1
        if k < 0:
            return False
        if stripped[k] in (")", "]"):
            return True
        if stripped[k].isalnum() or stripped[k] in ("_", "$"):
            m = k
            while m > 0 and (stripped[m - 1].isalnum() or stripped[m - 1] in ("_", "$")):
                m -= 1
            return stripped[m : k + 1] not in _JSX_PRECEDING_KEYWORDS
        return False

    def _find_matching_generic_end(self, stripped: str, start_idx: int) -> int | None:
        """Scans a balanced TypeScript generic '<...>' block and returns the end index, or None."""
        n = len(stripped)
        angle_depth = 1
        brace_depth = 0
        paren_depth = 0
        bracket_depth = 0
        j = start_idx + 1

        while j < n:
            if stripped[j : j + 2] in ("=>", ">=", "<="):
                j += 2
                continue
            ch = stripped[j]
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    return None
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth -= 1
                if paren_depth < 0:
                    return None
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1
                if bracket_depth < 0:
                    return None
            elif brace_depth == 0 and paren_depth == 0 and bracket_depth == 0:
                if ch == "<":
                    angle_depth += 1
                elif ch == ">":
                    angle_depth -= 1
                    if angle_depth == 0:
                        return j + 1
                elif ch == ";":
                    return None
            j += 1

        return None

    def _scan_jsx_opening_tag(self, stripped: str, start_idx: int) -> tuple[str, bool, int] | None:
        """Parses a JSX opening tag at start_idx, returning (tag_name, is_self_closing, end_idx)."""
        n = len(stripped)
        name_match = _JSX_TAG_NAME_RE.match(stripped, start_idx + 1)
        if not name_match:
            return None

        tag_name = name_match.group(0)
        pos = name_match.end()
        if pos < n and stripped[pos] == "<":
            generic_end = self._find_matching_generic_end(stripped, pos)
            if generic_end is None:
                return None
            pos = generic_end

        brace_depth = 0
        paren_depth = 0
        bracket_depth = 0

        while pos < n:
            ch = stripped[pos]
            if brace_depth == 0 and paren_depth == 0 and bracket_depth == 0:
                if stripped[pos : pos + 2] == "=>":
                    return None
                if ch in (",", ";", "<"):
                    return None
                if ch == ">":
                    body = stripped[name_match.end() : pos]
                    if _JSX_EXTENDS_RE.match(body):
                        return None
                    if _JSX_DEFAULT_TYPE_PARAM_RE.match(body) and stripped[
                        pos + 1 :
                    ].lstrip().startswith("("):
                        return None
                    k = pos - 1
                    while k > start_idx and stripped[k].isspace():
                        k -= 1
                    is_self_closing = k > start_idx and stripped[k] == "/"
                    return tag_name, is_self_closing, pos + 1

            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    return None
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth -= 1
                if paren_depth < 0:
                    return None
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1
                if bracket_depth < 0:
                    return None
            pos += 1

        return None

    def _check_jsx_tag_balance(self, stripped: str) -> list[str]:
        """Validates balanced JSX opening and closing tags while ignoring TypeScript generics."""
        tag_stack: list[str] = []
        i = 0
        n = len(stripped)

        while i < n:
            if stripped[i] != "<":
                i += 1
                continue

            if i + 1 < n and stripped[i + 1] in ("<", "="):
                i += 2
                continue

            if i + 1 < n and stripped[i + 1] == ">":
                tag_stack.append("__fragment__")
                i += 2
                continue

            if stripped[i : i + 3] == "</>":
                if not tag_stack:
                    return ["Unexpected closing tag </>"]
                expected_tag = tag_stack.pop()
                if expected_tag != "__fragment__":
                    return [f"Mismatched JSX tag: expected </{expected_tag}>, found </>"]
                i += 3
                continue

            close_match = _JSX_CLOSE_TAG_RE.match(stripped, i)
            if close_match:
                tag_name = close_match.group(1)
                if not tag_stack:
                    return [f"Unexpected closing tag </{tag_name}>"]
                expected_tag = tag_stack.pop()
                if expected_tag != tag_name:
                    return [f"Mismatched JSX tag: expected </{expected_tag}>, found </{tag_name}>"]
                i = close_match.end()
                continue

            if self._is_preceded_by_non_jsx_token(stripped, i):
                generic_end = self._find_matching_generic_end(stripped, i)
                i = generic_end if generic_end is not None else i + 1
                continue

            if i + 1 < n and stripped[i + 1].isalpha():
                parsed_tag = self._scan_jsx_opening_tag(stripped, i)
                if parsed_tag is not None:
                    tag_name, is_self_closing, end_idx = parsed_tag
                    if not (is_self_closing or tag_name.lower() in _JSX_VOID_ELEMENTS):
                        tag_stack.append(tag_name)
                    i = end_idx
                    continue
                generic_end = self._find_matching_generic_end(stripped, i)
                i = generic_end if generic_end is not None else i + 1
                continue

            i += 1

        if tag_stack:
            return [f"Unclosed JSX tag <{tag_stack[-1]}>"]
        return []

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

        # 2. JSX Tag balancing check (TypeScript-generic aware)
        tag_errors = self._check_jsx_tag_balance(stripped)
        if tag_errors:
            return False, tag_errors

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
