"""
Context-Aware Prompt Refiner and Metaprompt Synthesis Engine (IMP-0018).
Pre-processes incoming user prompts into structured engineering specifications
anchored in codebase AST and corporate invariants before pipeline submission.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from corporate_engineer.models import RevisedPromptSpec
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer

logger = logging.getLogger(__name__)

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # noqa: UP017 # type: ignore[assignment]


class ContextAwarePromptRefiner:
    """Refines human prompts into structured, context-aware metaprompt specifications."""

    DOMAIN_KEYWORDS: ClassVar[dict[str, dict[str, Any]]] = {
        "mcp": {
            "keywords": [
                "mcp",
                "tool",
                "sse",
                "stdio",
                "hub",
                "json-rpc",
                "circuit breaker",
                "client",
            ],
            "modules": [
                "src/corporate_engineer/mcp/client.py",
                "src/corporate_engineer/mcp/hub.py",
                "src/corporate_engineer/mcp/server.py",
            ],
        },
        "orchestrator": {
            "keywords": [
                "dag",
                "orchestrat",
                "parallel",
                "checkpoint",
                "rollback",
                "swarm",
                "fsm",
                "graph",
                "node",
            ],
            "modules": [
                "src/corporate_engineer/orchestrator/graph.py",
                "src/corporate_engineer/orchestrator/swarm.py",
            ],
        },
        "rag": {
            "keywords": ["ast", "index", "call graph", "inheritance", "parser", "syntax", "rag"],
            "modules": ["src/corporate_engineer/rag/ast_indexer.py"],
        },
        "system_one": {
            "keywords": [
                "system_one",
                "system-one",
                "decision",
                "nli",
                "outlines",
                "onnx",
                "benchmark",
                "slm",
                "qwen",
            ],
            "modules": [
                "src/corporate_engineer/system_one/router.py",
                "src/corporate_engineer/system_one/benchmark.py",
            ],
        },
        "quality": {
            "keywords": [
                "gate",
                "linter",
                "secret",
                "pre-flight",
                "clean",
                "storage",
                "mutation",
                "quality",
                "audit",
            ],
            "modules": [
                "src/corporate_engineer/quality/gate.py",
                "src/corporate_engineer/quality/storage_cleaner.py",
            ],
        },
        "cli": {
            "keywords": ["cli", "subcomando", "argument", "flag", "terminal", "parser"],
            "modules": [
                "src/corporate_engineer/cli/parser.py",
                "src/corporate_engineer/cli/main.py",
            ],
        },
    }

    BYPASS_EXACT: ClassVar[set[str]] = {
        "status",
        "ajuda",
        "help",
        "/preflight",
        "preflight",
    }

    BYPASS_PREFIXES: ClassVar[tuple[str, ...]] = (
        "git ",
        "pytest",
        "ruff ",
        "mypy",
        "python ",
        "dir",
        "ls",
    )

    def __init__(
        self,
        workspace_path: str | Path = ".",
        router: Any = None,
    ) -> None:
        self.workspace_path = Path(workspace_path)
        self.router = router

    def should_bypass(self, prompt: str) -> tuple[bool, str | None]:
        """Determine if a prompt is an operational command that bypasses metaprompting."""
        cleaned = prompt.strip()
        lowered = cleaned.lower()

        if lowered in self.BYPASS_EXACT:
            return True, "Operational command or short query detected: fast-path bypass enabled."

        for prefix in self.BYPASS_PREFIXES:
            if lowered.startswith(prefix):
                return (
                    True,
                    f"Operational command prefix '{prefix.strip()}' detected: fast-path bypass enabled.",
                )

        tokens = lowered.split()
        if len(tokens) <= 2 and not any(
            k in lowered for d in self.DOMAIN_KEYWORDS.values() for k in d["keywords"]
        ):
            return (
                True,
                "Brief query without actionable engineering scope: fast-path bypass enabled.",
            )

        return False, None

    def detect_domain(self, prompt: str) -> str:
        """Detect primary engineering domain from prompt keywords."""
        lowered = prompt.lower()
        domain_scores: dict[str, int] = {}

        for domain, meta in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in meta["keywords"] if kw in lowered)
            domain_scores[domain] = score

        best_domain = max(domain_scores, key=domain_scores.get)  # type: ignore[arg-type]
        if domain_scores[best_domain] > 0:
            return best_domain
        return "general"

    def find_ast_symbols(self, prompt: str) -> list[str]:
        """Search workspace AST or source files for symbols mentioned in prompt."""
        found_symbols: list[str] = []
        tokens = prompt.replace(",", " ").replace(".", " ").replace(":", " ").split()

        # Check for PascalCase or camelCase words in prompt
        candidate_words = [t for t in tokens if len(t) > 3 and (t[0].isupper() or "_" in t)]

        if not self.workspace_path.exists():
            return candidate_words

        # Fast-path: query CachedASTCodebaseIndexer in O(1) memory lookup
        try:
            indexer = CachedASTCodebaseIndexer(root_path=self.workspace_path)
            all_symbols = indexer.get_all_symbol_names()
            if all_symbols:
                for cand in candidate_words:
                    if cand in all_symbols and cand not in found_symbols:
                        found_symbols.append(cand)
                if found_symbols:
                    return found_symbols
        except (OSError, SyntaxError, ValueError, KeyError) as exc:
            logger.debug("Failed to resolve AST symbols from cache: %s", exc)

        src_dir = self.workspace_path / "src"
        if not src_dir.exists():
            src_dir = self.workspace_path

        for cand in candidate_words:
            # Search for class or def in workspace files (disk fallback)
            for py_file in src_dir.glob("**/*.py"):
                try:
                    text = py_file.read_text(encoding="utf-8", errors="ignore")
                    if (
                        f"class {cand}" in text or f"def {cand}" in text or cand in text
                    ) and cand not in found_symbols:
                        found_symbols.append(cand)
                except (OSError, UnicodeDecodeError):
                    pass

        return found_symbols

    def refine(
        self,
        prompt: str,
        bypass_gate: bool = False,
        extra_context: dict[str, Any] | None = None,
    ) -> RevisedPromptSpec:
        """Refine a prompt into a structured, context-aware metaprompt specification."""
        now_iso = datetime.now(UTC).isoformat()
        is_bypass, reason = self.should_bypass(prompt)

        if is_bypass and not bypass_gate:
            return RevisedPromptSpec(
                raw_prompt=prompt,
                target_domain="operational",
                core_intent=prompt.strip(),
                metaprompt=prompt,
                confidence_score=1.0,
                is_bypassed=True,
                bypass_reason=reason,
                timestamp=now_iso,
            )

        target_domain = self.detect_domain(prompt)
        meta = self.DOMAIN_KEYWORDS.get(target_domain, {"modules": ["src/corporate_engineer/"]})
        affected_modules = list(meta["modules"])

        ast_symbols = self.find_ast_symbols(prompt)

        # Core intent synthesis
        core_intent = prompt.strip()
        if len(core_intent) > 0:
            core_intent = core_intent[0].upper() + core_intent[1:]

        # Functional requirements
        functional_requirements: list[str] = [
            f"Analisar e projetar componentes estritamente no escopo do domínio '{target_domain}'.",
            "Definir e expor interfaces ou contratos fortemente tipados via Pydantic v2.",
            "Garantir isolamento defensivo de erros, timeouts e tratamento robusto de exceções.",
        ]
        if target_domain == "mcp":
            functional_requirements.append(
                "Integrar com MCPEnterpriseHub e aplicar isolamento por circuit breaker individual."
            )
        elif target_domain == "orchestrator":
            functional_requirements.append(
                "Garantir persistência de checkpoints e sincronização determinística de nós/agentes."
            )
        elif target_domain == "system_one":
            functional_requirements.append(
                "Validar inferência rápida sub-milissegundo com fallback transparente para heurísticas."
            )
        elif target_domain == "quality":
            functional_requirements.append(
                "Assegurar que as regras de auditoria e verificações de pre-flight sejam executadas."
            )
        elif target_domain == "cli":
            functional_requirements.append(
                "Registrar argumentos e flags no argparse da CLI corporativa com formatação padronizada."
            )

        # Non-functional requirements (Enterprise Invariants)
        non_functional_requirements: list[str] = [
            "Shift-Left TDD: Escrever testes automatizados unitários/integração (RED) antes da implementação (GREEN).",
            "Modelagem estrita Pydantic v2: Proibido uso de tipos soltos, `Any` desnecessário ou mutabilidade oculta.",
            "Pre-Flight Mandatório: 100% de aprovação em pytest, ruff check, mypy e secret_scanner.",
            "Imutabilidade e Padrões Corporativos: Respeitar limites de acoplamento e regras em AGENTS.md e GEMINI.md.",
        ]

        # Scope Guardrails (Out of Scope)
        out_of_scope: list[str] = [
            "Não introduzir alterações com quebra de retrocompatibilidade em APIs ou CLIs existentes.",
            f"Não realizar refatorações ou modificações fora do domínio '{target_domain}'.",
            "Não commitar segredos, credenciais ou caminhos absolutos locais de arquivos.",
        ]

        # TDD Verification Scenarios
        tdd_test_scenarios: list[str] = [
            f"test_{target_domain}_happy_path: Validação do fluxo principal de execução com parâmetros válidos.",
            f"test_{target_domain}_edge_cases: Comportamento com entradas vazias, nulas ou limites de dados.",
            f"test_{target_domain}_resilience_and_errors: Tratamento gracioso de falhas com mensagens informativas.",
        ]

        # Synthesize Metaprompt in Markdown
        bullet_modules = "\n".join(f"- `{m}`" for m in affected_modules)
        symbol_info = (
            f"- **Referenced Symbols**: {', '.join(f'`{s}`' for s in ast_symbols)}"
            if ast_symbols
            else ""
        )
        bullet_func = "\n".join(f"- [x] {req}" for req in functional_requirements)
        bullet_non_func = "\n".join(f"- {req}" for req in non_functional_requirements)
        bullet_scope = "\n".join(f"- {item}" for item in out_of_scope)
        bullet_tdd = "\n".join(f"- `{scen}`" for scen in tdd_test_scenarios)

        metaprompt_lines = [
            f"# Task Specification: {core_intent}",
            "",
            "## Raw Request",
            f"> {prompt}",
            "",
            "## Target Architecture & Modules",
            f"- **Target Domain**: `{target_domain}`",
            "- **Affected Modules**:",
            bullet_modules,
        ]
        if symbol_info:
            metaprompt_lines.append(symbol_info)

        metaprompt_lines.extend(
            [
                "",
                "## Functional Requirements",
                bullet_func,
                "",
                "## Corporate Non-Functional Requirements",
                bullet_non_func,
                "",
                "## Scope Guardrails",
                bullet_scope,
                "",
                "## TDD Verification Scenarios",
                bullet_tdd,
                "",
                "---",
                "*Generated automatically by Context-Aware Metaprompt Engine (IMP-0018).*",
            ]
        )
        metaprompt = "\n".join(metaprompt_lines)

        # Calculate confidence score
        confidence = 0.75
        if target_domain != "general":
            confidence += 0.10
        if ast_symbols:
            confidence += 0.05
        if len(prompt) > 20:
            confidence += 0.05
        confidence = min(0.98, round(confidence, 2))

        return RevisedPromptSpec(
            raw_prompt=prompt,
            target_domain=target_domain,
            core_intent=core_intent,
            functional_requirements=functional_requirements,
            non_functional_requirements=non_functional_requirements,
            affected_modules=affected_modules,
            out_of_scope=out_of_scope,
            tdd_test_scenarios=tdd_test_scenarios,
            metaprompt=metaprompt,
            confidence_score=confidence,
            is_bypassed=False,
            bypass_reason=None,
            timestamp=now_iso,
        )

    def format_output(self, spec: RevisedPromptSpec, format_type: str = "markdown") -> str:
        """Format a RevisedPromptSpec into text, json, or markdown."""
        if format_type == "json":
            return spec.model_dump_json(indent=2)
        elif format_type == "text":
            lines = [
                f"Target Domain: {spec.target_domain}",
                f"Bypassed: {spec.is_bypassed}",
                f"Core Intent: {spec.core_intent}",
                f"Confidence: {spec.confidence_score:.2f}",
                "",
                "Metaprompt:",
                spec.metaprompt,
            ]
            return "\n".join(lines)
        return spec.metaprompt
