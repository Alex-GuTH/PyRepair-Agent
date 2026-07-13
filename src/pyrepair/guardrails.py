"""Deterministic safety policy for actions emitted by the repair agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyrepair.models import Action, ActionType, GuardrailDecision, GuardrailDecisionType


BINARY_FILE_EXTENSIONS = frozenset(
    {
        ".7z",
        ".bmp",
        ".class",
        ".dll",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jar",
        ".jpeg",
        ".jpg",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".so",
        ".tar",
        ".webp",
        ".zip",
    }
)


@dataclass(frozen=True)
class GuardrailPolicy:
    """Safe defaults for file writes and pytest execution."""

    pytest_command: tuple[str, ...] = ("python", "-m", "pytest")


def evaluate_action(
    action: Action, project_root: Path, policy: GuardrailPolicy
) -> GuardrailDecision:
    """Return the deterministic policy decision for one parsed agent action."""
    if action.type is ActionType.READ_FILE:
        path = action.payload.get("path")
        if not isinstance(path, str):
            return _reject("invalid_path", "READ_FILE requires a string path.")
        resolved, decision = _resolve_project_path(path, project_root)
        if decision is not None:
            return decision
        if _is_sensitive(resolved):
            return _reject("sensitive_file", "Sensitive files cannot be read.")
        return _allow("read_allowed", "Read is inside the project and not sensitive.")

    if action.type is ActionType.APPLY_PATCH:
        if action.payload.get("operation") == "delete" or action.payload.get("delete") is True:
            return _reject("deletion_not_allowed", "File deletion is not allowed automatically.")

        paths, decision = _patch_paths(action)
        if decision is not None:
            return decision

        resolved_paths: list[Path] = []
        for path in paths:
            resolved, path_decision = _resolve_project_path(path, project_root)
            if path_decision is not None:
                return path_decision
            if _is_sensitive(resolved):
                return _reject("sensitive_file", "Sensitive files cannot be modified.")
            resolved_paths.append(resolved)

        root = project_root.resolve()
        if any(_is_binary(path) for path in resolved_paths):
            return _reject("binary_write_not_allowed", "Binary file writes are not allowed.")
        if any(_requires_write_approval(path, root) for path in resolved_paths):
            return _approval(
                "protected_write_approval_required",
                "This write targets a protected project file.",
            )
        if all(path.suffix.lower() == ".py" for path in resolved_paths):
            return _allow("source_write_allowed", "Ordinary Python source writes are allowed.")
        return _approval(
            "write_approval_required", "Only ordinary Python source writes are automatic."
        )

    if action.type is ActionType.RUN_TESTS:
        command = action.payload.get("command", list(policy.pytest_command))
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            return _reject("invalid_test_command", "RUN_TESTS requires a list of command strings.")
        if tuple(command) != policy.pytest_command:
            return _reject("test_command_mismatch", "Only the configured pytest command is allowed.")
        return _allow("test_command_allowed", "Configured pytest command is allowed.")

    if action.type in {ActionType.PROJECT_SCAN, ActionType.REQUEST_APPROVAL, ActionType.FINISH}:
        return _allow("non_file_action_allowed", "This action does not access or modify files.")
    return _reject("unsupported_action", "The action is not permitted by the guardrail policy.")


def _patch_paths(action: Action) -> tuple[list[str], GuardrailDecision | None]:
    paths: list[str] = []
    for key in ("path", "files_changed", "files"):
        if key not in action.payload:
            continue
        value = action.payload[key]
        if isinstance(value, str):
            paths.append(value)
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            paths.extend(value)
        else:
            return [], _reject("invalid_patch_path", "Patch paths must be strings or lists of strings.")
    if not paths:
        return [], _reject("missing_patch_path", "APPLY_PATCH requires at least one target path.")
    return paths, None


def _resolve_project_path(
    raw_path: str, project_root: Path
) -> tuple[Path, GuardrailDecision | None]:
    root = project_root.resolve()
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved, _reject("path_outside_project", "Path must remain inside the project root.")
    return resolved, None


def _is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    sensitive_markers = ("secret", "credential", "token", "private")
    return (
        name == ".env"
        or name.startswith(".env.")
        or any(marker in name for marker in sensitive_markers)
        or path.suffix.lower() in {".cer", ".crt", ".key", ".pem", ".p12", ".pfx"}
    )


def _is_binary(path: Path) -> bool:
    return path.suffix.lower() in BINARY_FILE_EXTENSIONS


def _requires_write_approval(path: Path, project_root: Path) -> bool:
    path_parts = tuple(part.lower() for part in path.relative_to(project_root).parts)
    parts = set(path_parts)
    name = path.name.lower()
    protected_names = {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        ".coveragerc",
        "pipfile",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        ".gitlab-ci.yml",
    }
    return (
        bool(parts & {"test", "tests", "docs", ".github", ".gitlab", ".circleci", "build", "dist", "__pycache__"})
        or any("generated" in part for part in path_parts)
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name in protected_names
        or name.startswith("requirements")
        or path.suffix.lower() in {".md", ".rst", ".txt", ".toml", ".ini", ".cfg", ".yaml", ".yml", ".lock", ".pyc"}
    )


def _allow(policy_code: str, reason: str) -> GuardrailDecision:
    return GuardrailDecision(GuardrailDecisionType.ALLOW, policy_code, reason)


def _reject(policy_code: str, reason: str) -> GuardrailDecision:
    return GuardrailDecision(GuardrailDecisionType.REJECT, policy_code, reason, "high")


def _approval(policy_code: str, reason: str) -> GuardrailDecision:
    return GuardrailDecision(
        GuardrailDecisionType.APPROVAL_REQUIRED, policy_code, reason, "medium"
    )
