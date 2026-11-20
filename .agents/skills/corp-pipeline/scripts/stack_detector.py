#!/usr/bin/env python3
"""
stack_detector.py - Universal Polyglot Stack Detector for Corporate Pipelines.
Inspects project roots to identify language, package manager, and deterministically
proposes commands for testing (test_cmd), linting (lint_cmd), and type checking (typecheck_cmd).
Includes IMP-0001: Automatic virtualenv (.venv/venv) detection and tool path resolution.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def find_files(root: Path, patterns: List[str]) -> List[str]:
    matches = []
    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_file():
                matches.append(p.name)
    return matches


def detect_stack(project_dir: Path) -> Dict[str, Any]:
    project_dir = project_dir.resolve()

    # Check for virtual environment (.venv or venv) - IMP-0001
    venv_dir: Path | None = None
    venv_detected = False
    for candidate in [".venv", "venv"]:
        cand_path = project_dir / candidate
        if cand_path.is_dir():
            venv_dir = cand_path
            venv_detected = True
            break

    # Determine bin directory for venv
    venv_bin_prefix: str | None = None
    if venv_dir is not None:
        if (venv_dir / "Scripts").is_dir() or (os.name == "nt" and (venv_dir / "Scripts").exists()):
            rel_path = venv_dir.relative_to(project_dir) if venv_dir.is_relative_to(project_dir) else venv_dir
            venv_bin_prefix = f"{rel_path}\\Scripts"
        elif (venv_dir / "bin").is_dir() or (venv_dir / "bin").exists():
            rel_path = venv_dir.relative_to(project_dir) if venv_dir.is_relative_to(project_dir) else venv_dir
            venv_bin_prefix = f"{rel_path}/bin"

    # Check Python
    py_markers = ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "setup.cfg"]
    detected_py = [m for m in py_markers if (project_dir / m).exists()]
    if detected_py:
        # Determine package manager / runner
        if (project_dir / "pyproject.toml").exists():
            content = (project_dir / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if "tool.uv" in content or "uv" in content:
                pkg_mgr = "uv"
                test_cmd = "uv run pytest"
                lint_cmd = "uv run ruff check ."
                typecheck_cmd = "uv run mypy ."
            elif "tool.poetry" in content:
                pkg_mgr = "poetry"
                test_cmd = "poetry run pytest"
                lint_cmd = "poetry run ruff check ."
                typecheck_cmd = "poetry run mypy ."
            else:
                pkg_mgr = "pip/pyproject"
                if venv_bin_prefix:
                    test_cmd = f"{venv_bin_prefix}\\pytest" if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/pytest"
                    lint_cmd = f"{venv_bin_prefix}\\ruff check ." if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/ruff check ."
                    typecheck_cmd = f"{venv_bin_prefix}\\mypy ." if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/mypy ."
                else:
                    test_cmd = "pytest"
                    lint_cmd = "ruff check ."
                    typecheck_cmd = "mypy ."
        elif (project_dir / "Pipfile").exists():
            pkg_mgr = "pipenv"
            test_cmd = "pipenv run pytest"
            lint_cmd = "pipenv run flake8"
            typecheck_cmd = "pipenv run mypy ."
        else:
            pkg_mgr = "pip"
            if venv_bin_prefix:
                test_cmd = f"{venv_bin_prefix}\\pytest" if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/pytest"
                lint_cmd = f"{venv_bin_prefix}\\ruff check ." if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/ruff check ."
                typecheck_cmd = f"{venv_bin_prefix}\\mypy ." if "\\" in venv_bin_prefix else f"{venv_bin_prefix}/mypy ."
            else:
                test_cmd = "pytest"
                lint_cmd = "ruff check ." if (project_dir / ".ruff.toml").exists() else "flake8"
                typecheck_cmd = "mypy ."

        return {
            "stack": "python",
            "detected_files": detected_py,
            "package_manager": pkg_mgr,
            "venv_detected": venv_detected,
            "venv_path": str(venv_dir) if venv_dir else None,
            "test_cmd": test_cmd,
            "lint_cmd": lint_cmd,
            "typecheck_cmd": typecheck_cmd,
            "root": str(project_dir),
        }

    # Check TypeScript / JavaScript
    if (project_dir / "package.json").exists():
        pkg_json_path = project_dir / "package.json"
        pkg_data = {}
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
        except Exception:
            pass

        scripts = pkg_data.get("scripts", {})
        has_ts = (project_dir / "tsconfig.json").exists() or "typescript" in pkg_data.get("devDependencies", {})

        # Package manager detection
        if (project_dir / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (project_dir / "yarn.lock").exists():
            pm = "yarn"
        elif (project_dir / "bun.lockb").exists():
            pm = "bun"
        else:
            pm = "npm"

        test_cmd = f"{pm} test" if "test" in scripts else (f"{pm} run test" if pm != "npm" else "npm test")
        lint_cmd = f"{pm} run lint" if "lint" in scripts else "npx eslint ."
        typecheck_cmd = f"{pm} run typecheck" if "typecheck" in scripts else ("npx tsc --noEmit" if has_ts else "echo 'No typecheck required for JS'")

        return {
            "stack": "typescript" if has_ts else "javascript",
            "detected_files": ["package.json"] + (["tsconfig.json"] if (project_dir / "tsconfig.json").exists() else []),
            "package_manager": pm,
            "test_cmd": test_cmd,
            "lint_cmd": lint_cmd,
            "typecheck_cmd": typecheck_cmd,
            "root": str(project_dir),
        }

    # Check Go
    if (project_dir / "go.mod").exists():
        return {
            "stack": "go",
            "detected_files": ["go.mod"],
            "package_manager": "go modules",
            "test_cmd": "go test ./...",
            "lint_cmd": "golangci-lint run",
            "typecheck_cmd": "go vet ./...",
            "root": str(project_dir),
        }

    # Check Rust
    if (project_dir / "Cargo.toml").exists():
        return {
            "stack": "rust",
            "detected_files": ["Cargo.toml"],
            "package_manager": "cargo",
            "test_cmd": "cargo test",
            "lint_cmd": "cargo clippy",
            "typecheck_cmd": "cargo check",
            "root": str(project_dir),
        }

    # Check Java / Kotlin
    if (project_dir / "pom.xml").exists():
        return {
            "stack": "java",
            "detected_files": ["pom.xml"],
            "package_manager": "maven",
            "test_cmd": "mvn test",
            "lint_cmd": "mvn checkstyle:check",
            "typecheck_cmd": "mvn test-compile",
            "root": str(project_dir),
        }
    if (project_dir / "build.gradle").exists() or (project_dir / "build.gradle.kts").exists():
        gradle_files = [f for f in ["build.gradle", "build.gradle.kts"] if (project_dir / f).exists()]
        wrapper = "./gradlew" if (project_dir / "gradlew").exists() or (project_dir / "gradlew.bat").exists() else "gradle"
        return {
            "stack": "java/kotlin",
            "detected_files": gradle_files,
            "package_manager": "gradle",
            "test_cmd": f"{wrapper} test",
            "lint_cmd": f"{wrapper} check",
            "typecheck_cmd": f"{wrapper} compileTestJava",
            "root": str(project_dir),
        }

    # Check C# / .NET
    sln_files = list(project_dir.glob("*.sln")) + list(project_dir.glob("*.csproj"))
    if sln_files:
        return {
            "stack": "csharp",
            "detected_files": [f.name for f in sln_files],
            "package_manager": "dotnet",
            "test_cmd": "dotnet test",
            "lint_cmd": "dotnet format --verify-no-changes",
            "typecheck_cmd": "dotnet build --no-restore",
            "root": str(project_dir),
        }

    # Check PHP
    if (project_dir / "composer.json").exists():
        return {
            "stack": "php",
            "detected_files": ["composer.json"],
            "package_manager": "composer",
            "test_cmd": "./vendor/bin/pest" if (project_dir / "vendor/bin/pest").exists() else "./vendor/bin/phpunit",
            "lint_cmd": "./vendor/bin/phpstan analyse" if (project_dir / "vendor/bin/phpstan").exists() else "php -l",
            "typecheck_cmd": "./vendor/bin/psalm" if (project_dir / "vendor/bin/psalm").exists() else "echo 'No typecheck required'",
            "root": str(project_dir),
        }

    # Fallback Generic
    return {
        "stack": "generic",
        "detected_files": [],
        "package_manager": "unknown",
        "test_cmd": "echo 'Configure your test_cmd in corp-pipeline config'",
        "lint_cmd": "echo 'Configure your lint_cmd in corp-pipeline config'",
        "typecheck_cmd": "echo 'Configure your typecheck_cmd in corp-pipeline config'",
        "root": str(project_dir),
    }


def main():
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    res = detect_stack(target_dir)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
