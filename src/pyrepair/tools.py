from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from pyrepair.models import PatchRecord, TestResult


def _resolve_project_path(project_root: Path, path: str | Path) -> Path:
    root = project_root.resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("path is outside project root") from error
    return candidate


class ProjectScanner:
    def scan(self, project_root: Path) -> dict[str, list[str]]:
        root = project_root.resolve()
        source_files: list[str] = []
        test_files: list[str] = []

        for file_path in sorted(root.rglob("*.py")):
            relative_path = file_path.relative_to(root).as_posix()
            if file_path.name.startswith("test_") or "tests" in file_path.parts:
                test_files.append(relative_path)
            else:
                source_files.append(relative_path)

        return {"source_files": source_files, "test_files": test_files}


class PytestRunner:
    def run(
        self,
        project_root: Path,
        command: list[str],
        timeout_seconds: int,
    ) -> TestResult:
        started_at = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return TestResult(
                command=command,
                exit_code=completed.returncode,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else ""
            return TestResult(
                command=command,
                exit_code=1,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                timed_out=True,
                stdout=stdout,
                stderr=stderr,
            )


class SafeFileReader:
    def read(self, project_root: Path, path: str) -> str:
        return _resolve_project_path(project_root, path).read_text(encoding="utf-8")


class PatchApplier:
    def apply_unified_diff(self, project_root: Path, diff_text: str) -> PatchRecord:
        root = project_root.resolve()
        file_patches = self._parse_file_patches(root, diff_text)
        updated_files: list[tuple[Path, str]] = []

        for path, hunks in file_patches:
            original_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            updated_files.append((path, self._apply_hunks(original_lines, hunks)))

        for path, content in updated_files:
            path.write_text(content, encoding="utf-8")

        return PatchRecord(
            files_changed=[path.relative_to(root).as_posix() for path, _ in updated_files],
            diff=diff_text,
            applied=True,
        )

    def _parse_file_patches(
        self,
        project_root: Path,
        diff_text: str,
    ) -> list[tuple[Path, list[list[str]]]]:
        lines = diff_text.splitlines(keepends=True)
        patches: list[tuple[Path, list[list[str]]]] = []
        index = 0

        while index < len(lines):
            if not lines[index].startswith("--- "):
                raise ValueError("expected unified diff file header")
            old_path = self._header_path(lines[index][4:])
            index += 1
            if index >= len(lines) or not lines[index].startswith("+++ "):
                raise ValueError("expected unified diff target header")
            new_path = self._header_path(lines[index][4:])
            index += 1
            self._resolve_diff_path(project_root, old_path)
            target_path = self._resolve_diff_path(project_root, new_path)
            self._validate_source_write(project_root, target_path)

            hunks: list[list[str]] = []
            while index < len(lines) and not lines[index].startswith("--- "):
                if not lines[index].startswith("@@ "):
                    raise ValueError("expected unified diff hunk header")
                if not re.match(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", lines[index]):
                    raise ValueError("invalid unified diff hunk header")
                hunk = [lines[index]]
                index += 1
                while index < len(lines) and not lines[index].startswith(("@@ ", "--- ")):
                    hunk.append(lines[index])
                    index += 1
                hunks.append(hunk)

            if not hunks:
                raise ValueError("unified diff contains no hunks")
            patches.append((target_path, hunks))

        if not patches:
            raise ValueError("unified diff is empty")
        return patches

    @staticmethod
    def _validate_source_write(project_root: Path, path: Path) -> None:
        relative_parts = tuple(part.lower() for part in path.relative_to(project_root).parts)
        protected_parts = {
            ".circleci",
            ".github",
            ".gitlab",
            "__pycache__",
            "config",
            "configs",
            "dist",
            "docs",
            "generated",
            "requirements",
            "test",
            "tests",
        }
        if (
            path.suffix != ".py"
            or bool(set(relative_parts) & protected_parts)
            or any("generated" in part for part in relative_parts)
            or path.name.startswith("test_")
            or path.name.endswith("_test.py")
        ):
            raise ValueError("patch target must be an ordinary Python source file")

    @staticmethod
    def _header_path(header: str) -> str:
        path = header.rstrip("\r\n").split("\t", 1)[0]
        if path == "/dev/null":
            raise ValueError("creating or deleting files is not supported")
        return path.removeprefix("a/").removeprefix("b/")

    @staticmethod
    def _resolve_diff_path(project_root: Path, path: str) -> Path:
        return _resolve_project_path(project_root, path)

    @staticmethod
    def _apply_hunks(original_lines: list[str], hunks: list[list[str]]) -> str:
        lines = original_lines[:]
        offset = 0
        for hunk in hunks:
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", hunk[0])
            if match is None:
                raise ValueError("invalid unified diff hunk header")
            old_start = int(match.group(1))
            start = (0 if old_start == 0 else old_start - 1) + offset
            expected: list[str] = []
            replacement: list[str] = []
            for line in hunk[1:]:
                if line.startswith("\\ No newline"):
                    continue
                if not line.startswith((" ", "+", "-")):
                    raise ValueError("invalid unified diff hunk line")
                content = line[1:]
                if line[0] in " -":
                    expected.append(content)
                if line[0] in " +":
                    replacement.append(content)
            if lines[start : start + len(expected)] != expected:
                raise ValueError("unified diff does not match file contents")
            lines[start : start + len(expected)] = replacement
            offset += len(replacement) - len(expected)
        return "".join(lines)
