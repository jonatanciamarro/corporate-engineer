"""
Quality and Verification CLI Commands (audit, test-surgical, fix, clean).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.quality.mutation import ASTMutationEngine


def register_audit_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `audit` command."""
    audit_parser = subparsers.add_parser("audit", help="Run pre-flight security and quality audit")
    audit_parser.add_argument("--path", default=".", help="Path to audit")
    audit_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    audit_parser.add_argument(
        "--strict", action="store_true", help="Run strict checks including test suite verification"
    )
    audit_parser.add_argument(
        "--mutation",
        action="store_true",
        help="Run AST mutation testing to evaluate test suite quality",
    )
    audit_parser.add_argument("--target-file", default=None, help="Specific source file to mutate")
    audit_parser.add_argument(
        "--max-mutants", type=int, default=10, help="Maximum number of mutants to test"
    )
    return audit_parser


def register_test_surgical_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `test-surgical` command."""
    surgical_parser = subparsers.add_parser(
        "test-surgical",
        help="Run surgical testing by detecting Git diff and computing affected tests via blast radius",
    )
    surgical_parser.add_argument(
        "--base-branch", default="main", help="Base Git branch for comparison (default: main)"
    )
    surgical_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Max transitive blast radius propagation depth (default: 3)",
    )
    surgical_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print affected tests and test command without executing",
    )
    surgical_parser.add_argument(
        "--fallback-all",
        action="store_true",
        help="Fallback to running all tests if changes exist but no tests match",
    )
    surgical_parser.add_argument("--workspace", default=".", help="Workspace path (default: .)")
    surgical_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    surgical_parser.add_argument(
        "--output", default=None, help="Optional file path to write output"
    )
    surgical_parser.add_argument(
        "pytest_extra_args", nargs="*", help="Optional extra arguments passed directly to pytest"
    )
    return surgical_parser


def register_fix_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `fix` command."""
    fix_parser = subparsers.add_parser(
        "fix",
        help="AST auto-refactor and self-healing code remediation engine (IMP-0012)",
    )
    fix_parser.add_argument(
        "--path",
        default=".",
        help="Target file or directory to auto-refactor (default: .)",
    )
    fix_parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically apply and write fixes to source files",
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate fixes and display diff without writing to disk",
    )
    fix_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    fix_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write fix report",
    )
    return fix_parser


def register_clean_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `clean` command."""
    clean_parser = subparsers.add_parser(
        "clean",
        help="Safe storage optimizer and disk hygiene engine (ADR-014)",
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate cleanup and display space to be freed without deleting",
    )
    clean_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return clean_parser


def handle_audit(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    runner = QualityGateRunner(project_root=target)
    secret_res = runner.run_secret_scan()

    test_res: dict[str, Any] | None = None
    strict_passed = True
    if args.strict:
        test_res = runner.run_tests()
        strict_passed = bool(test_res.get("passed", False))

    mutation_report = None
    if getattr(args, "mutation", False):
        engine = ASTMutationEngine(workspace_root=target)
        target_f: Path | None = None
        if getattr(args, "target_file", None):
            target_f = Path(args.target_file).resolve()
        else:
            for p in sorted(target.rglob("*.py")):
                if not any(
                    part.startswith(".") or part in ("venv", ".venv", "__pycache__", "tests")
                    for part in p.parts
                ):
                    target_f = p
                    break
        if target_f and target_f.exists():
            mutation_report = engine.run_mutation_testing(
                target_file=target_f, max_mutants=getattr(args, "max_mutants", 10)
            )

    overall_passed = bool(secret_res["passed"] and strict_passed)

    if args.format == "json":
        payload = {
            "passed": overall_passed,
            "secret_scan": secret_res,
            "findings": secret_res.get("findings", []),
            "strict_mode": args.strict,
            "test_verification": test_res,
            "mutation_report": mutation_report.model_dump() if mutation_report else None,
        }
        print(json.dumps(payload, indent=2))
    else:
        if secret_res["passed"]:
            print("✅ Pre-Flight Secret Scan PASS: Zero segredos detectados.")
        else:
            print("❌ Segredos encontrados:")
            for f in secret_res["findings"]:
                print(f" - {f['file']}:{f['line']} [{f['type']}]")

        if args.strict:
            if test_res and test_res["passed"]:
                print("✅ Strict Test Verification PASS: Todos os testes passaram.")
            else:
                print("❌ Strict Test Verification FAIL.")

        if mutation_report:
            print("🧬 AST Mutation Testing:")
            print(f"  - Total de Mutantes: {mutation_report.total_mutants}")
            print(f"  - Mutantes Mortos (Killed): {mutation_report.killed}")
            print(f"  - Mutantes Sobreviventes: {mutation_report.survived}")
            print(f"  - Mutation Score: {mutation_report.mutation_score}%")
            for m in mutation_report.mutants:
                status_icon = "💀 KILLED" if m.status == "KILLED" else "⚠️ SURVIVED"
                print(f"    [{status_icon}] L{m.line_number}: {m.original_op} -> {m.mutated_op}")

    return 0 if overall_passed else 1


def handle_test_surgical(args: argparse.Namespace) -> int:
    from corporate_engineer.quality.surgical_runner import SurgicalTestRunner

    runner = SurgicalTestRunner(root_path=Path(args.workspace).resolve())
    extra_args = args.pytest_extra_args if getattr(args, "pytest_extra_args", None) else None
    report = runner.run(
        base_branch=args.base_branch,
        max_depth=args.depth,
        dry_run=args.dry_run,
        fallback_all=args.fallback_all,
        extra_args=extra_args,
    )

    if args.format == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            "🔬 CORPORATE SURGICAL TDD RUNNER (IMP-0010)",
            "=" * 60,
            f"📌 Base Branch: {report.base_branch}",
            f"📂 Changed Files ({len(report.changed_files)}):",
        ]
        if report.changed_files:
            for f in report.changed_files:
                lines.append(f"   • {f}")
        else:
            lines.append("   (nenhum arquivo alterado detectado no Git diff / working tree)")

        lines.append(f"\n🎯 Affected Tests via Blast Radius ({len(report.affected_tests)}):")
        if report.affected_tests:
            for t in report.affected_tests:
                lines.append(f"   ⚡ {t}")
        else:
            lines.append("   (nenhum teste afetado detectado)")

        if report.command:
            lines.append(f"\n⚙️  Command: {report.command}")

        if report.executed:
            status_symbol = "✅ PASS" if report.passed else "❌ FAIL"
            lines.append(f"⏱️  Duration: {report.duration_ms:.2f} ms")
            lines.append(f"📊 Result: {status_symbol} (exit code: {report.exit_code})")
            if report.stdout:
                lines.append("\n--- Pytest Output ---")
                lines.append(report.stdout.strip())
            if report.stderr:
                lines.append("\n--- Pytest Stderr ---")
                lines.append(report.stderr.strip())
        elif report.affected_tests:
            lines.append("ℹ️  Dry-run mode: testes não executados.")

        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório de teste cirúrgico salvo em: {out_p}")
    else:
        print(output_str)

    return report.exit_code if report.executed else 0


def handle_fix(args: argparse.Namespace) -> int:
    from corporate_engineer.eval.fixer import ASTSelfHealingFixer

    fixer = ASTSelfHealingFixer()
    target_path = Path(args.path).resolve()

    dry_run = not args.auto or args.dry_run

    if target_path.is_file():
        report = fixer.fix_file(target_path, dry_run=dry_run)
    else:
        report = fixer.fix_workspace(target_path, dry_run=dry_run)

    if args.format == "json":
        output_str = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
    else:
        status_mode = (
            "[DRY RUN - SEM ESCRITA]" if report.dry_run else "[AUTO FIX - MODIFICAÇÕES GRAVADAS]"
        )
        lines = [
            f"\n{'=' * 60}",
            "🛠️  AST Auto-Refactor & Self-Healing Fixer (IMP-0012)",
            f"{'=' * 60}",
            f"📁 Alvo               : {target_path}",
            f"⚙️  Modo               : {status_mode}",
            f"📊 Arquivos Analisados: {report.total_files_analyzed}",
            f"✏️  Arquivos Modificados: {report.files_modified}",
            f"🔧 Correções Aplicadas: {len(report.fixes_applied)}",
            f"🛡️  Risco Sistema 1    : {report.system_one_risk}",
            f"{'-' * 60}",
        ]
        if report.fixes_applied:
            lines.append("📋 Detalhes das Correções:")
            for fix in report.fixes_applied:
                lines.append(
                    f"   • [{fix.rule_name}] {fix.file_path}:{fix.line_number} - {fix.description}"
                )
        else:
            lines.append("✨ Nenhuma inconformidade estrutural detectada.")
        lines.append(f"{'=' * 60}\n")
        output_str = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output_str, encoding="utf-8")
        print(f"Relatório de correções salvo em: {args.output}")
    else:
        print(output_str)

    return 0


def handle_clean(args: argparse.Namespace) -> int:
    from corporate_engineer.quality.storage_cleaner import SafeStorageCleaner

    cleaner = SafeStorageCleaner()
    report = cleaner.clean_all(dry_run=args.dry_run)

    if args.format == "json":
        output_str = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
    else:
        status_mode = "[SIMULAÇÃO / DRY RUN]" if report.dry_run else "[LIMPEZA EXECUTADA]"
        lines = [
            f"\n{'=' * 60}",
            "🧹  Safe Storage Optimizer & Disk Hygiene Engine (ADR-014)",
            f"{'=' * 60}",
            f"⚙️  Modo               : {status_mode}",
            f"📊 Total Liberado     : {report.total_freed_gb} GB ({report.total_freed_bytes:,} bytes)",
            f"🎯 Alvos Processados  : {len(report.results)}",
            f"{'-' * 60}",
        ]
        for res in report.results:
            status_symbol = "✅" if res.success else "❌"
            error_msg = f" ({res.error})" if res.error else ""
            mb = round(res.freed_bytes / (1024**2), 2)
            lines.append(f"   {status_symbol} [{res.target_name}] {res.path} -> {mb} MB{error_msg}")
        lines.append(f"{'=' * 60}\n")
        output_str = "\n".join(lines)

    print(output_str)
    return 0
