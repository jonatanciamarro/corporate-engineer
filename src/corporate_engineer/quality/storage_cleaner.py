"""
Safe Storage Optimizer & Disk Hygiene Engine for Corporate Environments.
"""

import os
import shutil
from pathlib import Path
from typing import ClassVar

from corporate_engineer.models import (
    StorageCleanResult,
    StorageOptimizationReport,
    StorageTarget,
)


class SafeStorageCleaner:
    """
    Scans and safely purges caches, orphaned models, and temporary files
    while strictly protecting user personal files and code repositories.
    """

    FORBIDDEN_DIR_NAMES: ClassVar[set[str]] = {
        "desktop",
        "documents",
        "music",
        "pictures",
        "videos",
        "downloads",
        "onedrive",
        ".ssh",
        ".aws",
    }

    def __init__(self, workspace_path: str | Path | None = None) -> None:
        self.workspace_path = (
            Path(workspace_path).resolve() if workspace_path else Path.cwd().resolve()
        )

    def is_path_safe(self, target_path: str | Path) -> bool:
        """
        Determines whether a path is strictly safe to clean.
        Rejects personal directories and current workspace paths.
        """
        resolved = Path(target_path).resolve()

        # Reject workspace and subpaths of workspace
        try:
            if resolved == self.workspace_path or self.workspace_path in resolved.parents:
                return False
        except (ValueError, OSError):
            return False

        # Check against forbidden directory names in any part of path
        parts_lower = [p.lower() for p in resolved.parts]
        for forbidden in self.FORBIDDEN_DIR_NAMES:
            if forbidden in parts_lower:
                return False

        return True

    def calculate_size(self, path: Path) -> int:
        """
        Calculates total size in bytes for a file or directory.
        """
        if not path.exists():
            return 0
        if path.is_file():
            try:
                return path.stat().st_size
            except OSError:
                return 0

        total = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        fp = Path(root) / f
                        total += fp.stat().st_size
                    except OSError:
                        continue
        except OSError:
            pass
        return total

    def scan_standard_targets(self) -> list[StorageTarget]:
        """
        Scans common system and framework caches.
        """
        targets: list[StorageTarget] = []
        user_home = Path.home()
        local_app_data = Path(os.environ.get("LOCALAPPDATA", user_home / "AppData" / "Local"))

        candidates = [
            ("cache", "pip_cache", local_app_data / "pip" / "cache", "Pip package wheel cache"),
            (
                "cache",
                "npm_cache",
                local_app_data / "npm-cache",
                "Node package manager global cache",
            ),
            (
                "model",
                "gpt4all_wizardlm",
                local_app_data / "nomic.ai" / "GPT4All" / "WizardLM-7B-uncensored.Q4_0.gguf",
                "Local GPT4All WizardLM model weight",
            ),
            (
                "model",
                "ollama_models",
                user_home / ".ollama" / "models",
                "Ollama local model blobs and manifests",
            ),
            (
                "audio_cache",
                "spotify_cache",
                local_app_data / "Spotify" / "Data",
                "Spotify offline song chunks cache",
            ),
            (
                "cache",
                "torch_cache",
                user_home / ".cache" / "torch",
                "PyTorch checkpoint and hub cache",
            ),
            (
                "cache",
                "huggingface_cache",
                user_home / ".cache" / "huggingface",
                "Hugging Face hub cache",
            ),
        ]

        for cat, name, p, desc in candidates:
            if p.exists():
                size = self.calculate_size(p)
                if size > 0:
                    targets.append(
                        StorageTarget(
                            category=cat,
                            name=name,
                            path=str(p),
                            size_bytes=size,
                            is_safe=self.is_path_safe(p),
                            description=desc,
                        )
                    )

        return targets

    def clean_target(self, target: StorageTarget, dry_run: bool = False) -> StorageCleanResult:
        """
        Cleans a single target path safely.
        """
        target_path = Path(target.path)

        if not target.is_safe or not self.is_path_safe(target_path):
            return StorageCleanResult(
                target_name=target.name,
                path=target.path,
                freed_bytes=0,
                success=False,
                error="Path deemed unsafe or forbidden for deletion.",
            )

        if not target_path.exists():
            return StorageCleanResult(
                target_name=target.name,
                path=target.path,
                freed_bytes=0,
                success=True,
                error="Path does not exist.",
            )

        freed_bytes = (
            target.size_bytes if target.size_bytes > 0 else self.calculate_size(target_path)
        )

        if dry_run:
            return StorageCleanResult(
                target_name=target.name,
                path=target.path,
                freed_bytes=freed_bytes,
                success=True,
            )

        try:
            if target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                shutil.rmtree(target_path)
            return StorageCleanResult(
                target_name=target.name,
                path=target.path,
                freed_bytes=freed_bytes,
                success=True,
            )
        except (OSError, RuntimeError) as exc:
            return StorageCleanResult(
                target_name=target.name,
                path=target.path,
                freed_bytes=0,
                success=False,
                error=str(exc),
            )

    def clean_all(
        self,
        targets: list[StorageTarget] | None = None,
        dry_run: bool = False,
    ) -> StorageOptimizationReport:
        """
        Executes cleanup across a list of targets (or standard targets if None).
        """
        if targets is None:
            targets = self.scan_standard_targets()

        results: list[StorageCleanResult] = []
        total_freed = 0

        for tgt in targets:
            res = self.clean_target(tgt, dry_run=dry_run)
            results.append(res)
            if res.success:
                total_freed += res.freed_bytes

        total_gb = round(total_freed / (1024**3), 2)
        return StorageOptimizationReport(
            total_freed_bytes=total_freed,
            total_freed_gb=total_gb,
            results=results,
            dry_run=dry_run,
        )
