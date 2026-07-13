# PyRepair Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build PyRepair Agent, a Python + pytest test-repair coding agent harness with deterministic mock-LLM tests, safety guardrails, CLI, WebUI, CI, distribution, and process evidence.

**Architecture:** The project is a Python package with a self-implemented agent loop. CLI and WebUI call a shared run controller, which uses injectable LLM clients, strict action parsing, guardrail checks, tool dispatch, pytest feedback parsing, and an append-only run store.

**Tech Stack:** Python, pytest, Typer, FastAPI, OpenAI-compatible chat completion API, mock LLM, JSONL run logs, Docker, GitHub Actions, GitLab CI.

## Global Constraints

- First version supports Python projects that use pytest.
- Default automatic writes are limited to ordinary `.py` source files outside test paths.
- Test files, dependency files, configuration files, CI files, documentation, lock files, file deletion, and writes outside the project require approval or rejection by guardrails.
- The LLM never receives arbitrary shell access.
- Real LLM mode uses an OpenAI-compatible API; mock LLM mode is required for deterministic tests.
- API keys must not be committed, logged, printed, displayed in WebUI, or stored in plaintext config.
- Offline tests must not require network access or real API keys.
- Canonical offline test command is `make test`.
- Public WebUI deployment is mock/demo-only.
- Provide both GitHub Actions and `.gitlab-ci.yml`; `.gitlab-ci.yml` must contain a `unit-test` job.
- Use TDD for implementation tasks: write a failing test, verify red, implement minimal code, verify green, refactor if needed.
- Use worktree-backed feature branches and PR/MR evidence for major modules.
- Update `PLAN.md` and `AGENT_LOG.md` after each task with completion status and commit hash.

---

## Implementation Preconditions

- [ ] Move `SPEC.md` and this `PLAN.md` into the final course repository, or initialize the current directory as the final repository after human confirmation.
- [ ] Stop before implementation if `git status --short` fails with "not a git repository".
- [ ] Create the main branch and remote before feature work, so worktree, branch, PR/MR, commit, and CI evidence are collected from the start.
- [ ] Create `SPEC_PROCESS.md` before implementation and record this brainstorming session summary, at least three key iterations, and accepted/rejected design decisions.
- [ ] Run cold-start validation with a different agent after `SPEC.md` and `PLAN.md` are approved. Give that agent only `SPEC.md` and `PLAN.md`, ask it to attempt one or two early tasks, and record gaps in `SPEC_PROCESS.md`.

## File Structure

```text
.
├── SPEC.md
├── PLAN.md
├── SPEC_PROCESS.md
├── AGENT_LOG.md
├── REFLECTION.md
├── README.md
├── Makefile
├── Dockerfile
├── pyproject.toml
├── .gitignore
├── .gitlab-ci.yml
├── .github/
│   └── workflows/
│       └── unit-test.yml
├── src/
│   └── pyrepair/
│       ├── __init__.py
│       ├── actions.py
│       ├── cli.py
│       ├── config.py
│       ├── core.py
│       ├── credentials.py
│       ├── feedback.py
│       ├── guardrails.py
│       ├── llm.py
│       ├── models.py
│       ├── run_controller.py
│       ├── store.py
│       ├── tools.py
│       └── web/
│           ├── __init__.py
│           ├── app.py
│           └── static/
│               ├── app.js
│               └── styles.css
├── tests/
│   ├── test_actions.py
│   ├── test_cli.py
│   ├── test_core_loop.py
│   ├── test_credentials.py
│   ├── test_feedback.py
│   ├── test_guardrails.py
│   ├── test_store.py
│   ├── test_tools.py
│   └── test_web.py
└── examples/
    └── buggy_calculator/
        ├── src/
        │   └── calculator.py
        └── tests/
            └── test_calculator.py
```

## Branch and PR Plan

- `feature/scaffold-and-process`: Tasks 1 and 2.
- `feature/models-actions-guardrails`: Tasks 3 and 4.
- `feature/feedback-tools-store`: Tasks 5, 6, and 7.
- `feature/core-loop-demos`: Tasks 8 and 9.
- `feature/cli-credentials-web`: Tasks 10, 11, and 12.
- `feature/ci-distribution-docs`: Tasks 13 and 14.

Each feature branch must have a PR/MR or equivalent review record with PLAN task ids, subagent identity, TDD red/green/refactor summary, manual changes, verification commands, and risk notes.

---

### Task 1: Repository Scaffold and Process Files

**Status:** Implemented in scaffold commit `1a33db8`; canonical `make test` could
not be executed locally because no Make implementation is installed in the
current Windows environment. Equivalent underlying verification
`python -m pytest -q` passed and `make test` remains required in CI.

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `src/pyrepair/__init__.py`
- Create: `tests/test_package_import.py`
- Modify: `AGENT_LOG.md`
- Modify: `SPEC_PROCESS.md`

**Interfaces:**
- Produces package import name: `pyrepair`
- Produces canonical test command: `make test`
- Produces process evidence files used by all later tasks.

- [x] **Step 1: Confirm repository state**

Run: `git status --short`

Expected: command succeeds. If it fails because the directory is not a Git repository, stop and ask the human owner to confirm initializing or moving to the final repository.

- [x] **Step 2: Create a worktree-backed branch**

Run from the final repository root:

```bash
git switch -c feature/scaffold-and-process
```

Expected: branch switches to `feature/scaffold-and-process`.

- [x] **Step 3: Write the failing import test**

Create `tests/test_package_import.py` with this test:

```python
def test_pyrepair_package_imports():
    import pyrepair

    assert pyrepair.__version__ == "0.1.0"
```

- [x] **Step 4: Run the test to verify red**

Run: `python -m pytest tests/test_package_import.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'pyrepair'` or missing `__version__`.

- [x] **Step 5: Add minimal package metadata**

Create `pyproject.toml` defining package name `pyrepair-agent`, Python version floor `>=3.11`, package source under `src`, and dev dependencies for pytest.

Create `src/pyrepair/__init__.py` exporting `__version__ = "0.1.0"`.

- [x] **Step 6: Add canonical test command**

Create `Makefile` with a `test` target that runs:

```bash
python -m pytest -q
```

- [x] **Step 7: Update process evidence files**

Ensure `AGENT_LOG.md` has columns for timestamp, task id, Superpowers skill, context, subagent summary, commit/PR link, human intervention, and lesson learned.

Ensure `SPEC_PROCESS.md` has sections for brainstorming iterations, accepted/rejected suggestions, cold-start validation, and SPEC/PLAN revisions.

- [x] **Step 8: Add `.gitignore`**

Include Python caches, virtual environments, build outputs, `.env`, local run logs, local key files, and OS/editor noise.

- [x] **Step 9: Run green verification**

Run: `make test`

Expected: PASS.

Local note: `make` was unavailable in the current Windows environment, so the
underlying command `python -m pytest -q` was run and passed with `1 passed`.
CI must still execute `make test` on an environment with Make installed.

- [x] **Step 10: Commit and record evidence**

Run:

```bash
git add .gitignore pyproject.toml Makefile src/pyrepair/__init__.py tests/test_package_import.py AGENT_LOG.md SPEC_PROCESS.md PLAN.md SPEC.md
git commit -m "chore: scaffold PyRepair Agent project"
```

Update `PLAN.md` Task 1 status and `AGENT_LOG.md` with the commit hash.

Scaffold commit: `1a33db8`. Evidence recording is stored in a follow-up docs
commit to avoid self-referential amend loops.

---

### Task 2: Cold-Start Validation and SPEC_PROCESS Update

**Status:** Implemented in `adddd27`; cold-start validation found real
model-contract ambiguity, and `SPEC.md` plus `PLAN.md` were revised before
implementation continued.

**Files:**
- Modify: `SPEC_PROCESS.md`
- Modify: `PLAN.md`
- Modify: `AGENT_LOG.md`

**Interfaces:**
- Consumes approved `SPEC.md` and `PLAN.md`.
- Produces recorded cold-start feedback before implementation proceeds.

- [x] **Step 1: Start a different agent session**

Use a different agent type from the main development agent. Provide only `SPEC.md` and `PLAN.md`.

- [x] **Step 2: Ask it to attempt one early task**

Prompt requirement:

```text
Read SPEC.md and PLAN.md only. Attempt Task 3 or Task 4. If any requirement is ambiguous, stop and ask rather than guessing.
```

- [x] **Step 3: Record the result**

In `SPEC_PROCESS.md`, record where the agent paused, what it misunderstood, and whether the issue came from the SPEC/PLAN or the agent.

- [x] **Step 4: Revise SPEC or PLAN if needed**

If the cold-start agent reveals a real ambiguity, patch `SPEC.md` or `PLAN.md` before implementation continues.

- [x] **Step 5: Commit and record evidence**

Run:

```bash
git add SPEC.md PLAN.md SPEC_PROCESS.md AGENT_LOG.md
git commit -m "docs: record cold-start validation"
```

Update `PLAN.md` Task 2 status and `AGENT_LOG.md` with the commit hash.

Cold-start documentation commit: `adddd27`. Evidence hash recording is stored in
a follow-up docs commit to avoid self-referential amend loops.

---

### Task 3: Core Data Models

**Status:** Implemented in `d980115`; TDD red verification confirmed the missing
`pyrepair.models` module and green verification passed.

**Files:**
- Create: `src/pyrepair/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces enums:
  - `ActionType`: `PROJECT_SCAN`, `RUN_TESTS`, `READ_FILE`, `APPLY_PATCH`, `REQUEST_APPROVAL`, `FINISH`.
  - `RunStatus`: `RUNNING`, `PASSED`, `FAILED`, `WAITING_APPROVAL`, `CANCELLED`.
  - `GuardrailDecisionType`: `ALLOW`, `REJECT`, `APPROVAL_REQUIRED`.
  - `FailureCategory`: `NONE`, `ASSERTION_FAILURE`, `RUNTIME_EXCEPTION`, `IMPORT_ERROR`, `SYNTAX_ERROR`, `COLLECTION_ERROR`, `TIMEOUT`, `UNKNOWN_FAILURE`.
  - `TestStatus`: `PASSED`, `FAILED`, `ERROR`, `TIMEOUT`.
  - `ApprovalStatus`: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`.
  - `LLMProvider`: `MOCK`, `OPENAI_COMPATIBLE`.
  - `ActionParseStatus`: `PARSED`, `INVALID_JSON`, `UNKNOWN_ACTION`, `MISSING_FIELD`, `INVALID_PAYLOAD`.
- Produces dataclasses with exact fields:
  - `Action(type: ActionType, payload: dict[str, object] = field(default_factory=dict), raw_model_output: str = "", parse_status: ActionParseStatus = ActionParseStatus.PARSED)`.
  - `GuardrailDecision(decision: GuardrailDecisionType, policy_code: str = "", reason: str = "", risk_level: str = "low")`.
  - `FailureSummary(status: TestStatus = TestStatus.FAILED, category: FailureCategory = FailureCategory.UNKNOWN_FAILURE, failed_tests: list[str] = field(default_factory=list), related_files: list[str] = field(default_factory=list), traceback_excerpt: str = "", line_hints: list[int] = field(default_factory=list), message: str = "")`.
  - `TestResult(command: list[str] = field(default_factory=list), exit_code: int = 0, duration_ms: int = 0, timed_out: bool = False, stdout: str = "", stderr: str = "", raw_output_ref: str = "", failure_summary: FailureSummary | None = None)`.
  - `PatchRecord(files_changed: list[str] = field(default_factory=list), diff: str = "", applied: bool = False, requires_approval: bool = False, source_step: int | None = None)`.
  - `ToolResult(tool_name: str, success: bool = False, stdout_summary: str = "", stderr_summary: str = "", exit_code: int | None = None, changed_files: list[str] = field(default_factory=list), error: str = "", test_result: TestResult | None = None, patch_record: PatchRecord | None = None)`.
  - `RunStep(run_id: str, round_index: int, llm_backend: str = "", context_summary: str = "", action: Action | None = None, guardrail_decision: GuardrailDecision | None = None, tool_result: ToolResult | None = None, feedback: FailureSummary | None = None, created_at: str = "")`.
  - `RunRecord(id: str, project_root: str, status: RunStatus = RunStatus.RUNNING, created_at: str = "", updated_at: str = "", max_rounds: int = 3, current_round: int = 0, steps: list[RunStep] = field(default_factory=list), final_summary: str = "")`.
  - `ApprovalRequest(id: str, run_id: str, step_id: str = "", action: Action | None = None, reason: str = "", diff: str = "", status: ApprovalStatus = ApprovalStatus.PENDING, decision_note: str = "")`.
  - `LLMConfig(provider: LLMProvider = LLMProvider.MOCK, base_url: str = "", model: str = "", api_key_ref: str = "", timeout_seconds: int = 60, max_output_tokens: int = 2048)`.
- Produces helper functions `to_jsonable(value: object) -> object` and `dataclass_to_dict(value: object) -> dict[str, object]` that serialize enums as strings and nested dataclasses recursively.
- Later tasks import these models directly from `pyrepair.models`.

- [ ] **Step 1: Write failing model tests**

Create `tests/test_models.py` with tests that construct:

```python
from pyrepair.models import (
    Action,
    ActionType,
    FailureCategory,
    FailureSummary,
    TestResult,
    TestStatus,
    dataclass_to_dict,
)


def test_action_model_preserves_type_and_payload():
    action = Action(type=ActionType.READ_FILE, payload={"path": "src/app.py"})
    assert action.type is ActionType.READ_FILE
    assert action.type.value == "READ_FILE"
    assert action.payload["path"] == "src/app.py"


def test_failure_summary_defaults_to_empty_collections():
    summary = FailureSummary(category=FailureCategory.ASSERTION_FAILURE)
    assert summary.status is TestStatus.FAILED
    assert summary.failed_tests == []
    assert summary.related_files == []


def test_nested_test_result_accepts_failure_summary():
    summary = FailureSummary(
        category=FailureCategory.SYNTAX_ERROR,
        related_files=["src/app.py"],
        line_hints=[3],
    )
    result = TestResult(
        command=["python", "-m", "pytest"],
        exit_code=2,
        failure_summary=summary,
    )
    assert result.failure_summary is summary
    assert result.failure_summary.related_files == ["src/app.py"]


def test_model_serialization_uses_enum_values():
    action = Action(type=ActionType.RUN_TESTS)
    data = dataclass_to_dict(action)
    assert data["type"] == "RUN_TESTS"
    assert data["parse_status"] == "PARSED"
```

- [ ] **Step 2: Run red verification**

Run: `python -m pytest tests/test_models.py -q`

Expected: FAIL because `pyrepair.models` does not exist.

- [ ] **Step 3: Implement minimal models**

Create enums, dataclasses, and serialization helpers named in the Interfaces block. Use `dataclasses.field(default_factory=list)` for every list field. Use `from __future__ import annotations` so union types can reference later dataclasses safely.

- [ ] **Step 4: Run green verification**

Run: `python -m pytest tests/test_models.py -q`

Expected: PASS.

- [ ] **Step 5: Commit and record evidence**

Run:

```bash
git add src/pyrepair/models.py tests/test_models.py PLAN.md AGENT_LOG.md
git commit -m "feat: add core run and action models"
```

Update `PLAN.md` Task 3 status and `AGENT_LOG.md` with the commit hash.

---

### Task 4: Strict Action Parser

**Status:** Implemented in `d5f1e01`; TDD red verification confirmed the
missing `pyrepair.actions` module, and green verification passed `7 passed`.
Evidence hash recording commit: `511d841`; this review-fix commit records
that hash separately to avoid self-reference.

**Files:**
- Create: `src/pyrepair/actions.py`
- Create: `tests/test_actions.py`

**Interfaces:**
- Consumes `Action` and `ActionType` from `pyrepair.models`.
- Produces `parse_action(raw: str) -> Action`.
- Raises `ActionParseError` for malformed JSON, unknown action types, missing payload, or non-object payload.

- [x] **Step 1: Write failing parser tests**

Create tests for valid JSON, malformed JSON, unknown action type, and missing payload:

```python
import pytest

from pyrepair.actions import ActionParseError, parse_action
from pyrepair.models import ActionType


def test_parse_valid_read_file_action():
    action = parse_action('{"type":"READ_FILE","payload":{"path":"src/app.py"}}')
    assert action.type is ActionType.READ_FILE
    assert action.payload == {"path": "src/app.py"}


def test_rejects_unknown_action_type():
    with pytest.raises(ActionParseError):
        parse_action('{"type":"SHELL","payload":{"command":"rm -rf ."}}')
```

- [x] **Step 2: Run red verification**

Run: `python -m pytest tests/test_actions.py -q`

Expected: FAIL because `pyrepair.actions` does not exist.

- [x] **Step 3: Implement parser and exception**

Implement `ActionParseError` and `parse_action`. The parser must call `json.loads`, require a JSON object, map `type` to `ActionType`, require `payload` to be a dict, and preserve raw model output on the returned `Action`.

- [x] **Step 4: Run green verification**

Run: `python -m pytest tests/test_actions.py -q`

Expected: PASS.

- [x] **Step 5: Commit and record evidence**

Run:

```bash
git add src/pyrepair/actions.py tests/test_actions.py PLAN.md AGENT_LOG.md
git commit -m "feat: add strict action parser"
```

Update `PLAN.md` Task 4 status and `AGENT_LOG.md` with the commit hash.

---

### Task 5: Guardrail Engine

**Status:** Implemented in `573a2da`; TDD red verification confirmed the missing
`pyrepair.guardrails` module, and green verification passed `8 passed`.
Evidence hash recording commit: `065ed55`; this hash-recording commit records
that value separately to avoid self-reference.
Review fix commit: `c1e54c6`; adds generated-path approval, binary-write
rejection, and certificate-file protection with regression TDD evidence.
Second review fix commit: `8e200ff`; rejects `.bin` and unknown extensionless
writes while keeping known protected text/config targets approval-required.
Evidence hash recording commit: `88d72c8`.
Third review fix commit: `0feab4d`; rejects unknown-extension writes while
retaining known protected text/config targets. No separate evidence commit was
recorded.
Fourth review-fix commit: `89820f8`; rejects compiled Python writes before
protected-path handling and requires approval for protected unknown text
suffixes.
Fifth review-fix commit: `3fa761f`; requires approval for protected config and
dependency directories such as `config/` and `requirements/`.
Fifth review-fix evidence commit: `131e053`.
Sixth review-fix commit: `2f12973`; rejects conventional private identity-key
paths such as `id_rsa` and `id_ed25519` as sensitive files.
Sixth review-fix evidence commit: `61b1bb6`.
Seventh review-fix commit: `8b94d25`; protects common secret filenames and
requires approval for root-level common configuration files.
Seventh review-fix evidence commit: `56e1fc3`.

**Files:**
- Create: `src/pyrepair/guardrails.py`
- Create: `tests/test_guardrails.py`

**Interfaces:**
- Consumes `Action`, `ActionType`, `GuardrailDecision`, `GuardrailDecisionType`.
- Produces `GuardrailPolicy` dataclass.
- Produces `evaluate_action(action: Action, project_root: Path, policy: GuardrailPolicy) -> GuardrailDecision`.

- [ ] **Step 1: Write failing path and sensitive-file tests**

Test cases:

```python
from pathlib import Path

from pyrepair.guardrails import GuardrailPolicy, evaluate_action
from pyrepair.models import Action, ActionType, GuardrailDecisionType


def test_rejects_read_outside_project(tmp_path):
    action = Action(type=ActionType.READ_FILE, payload={"path": "../secret.txt"})
    decision = evaluate_action(action, tmp_path, GuardrailPolicy())
    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "path_outside_project"


def test_rejects_env_file_read(tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret")
    action = Action(type=ActionType.READ_FILE, payload={"path": ".env"})
    decision = evaluate_action(action, tmp_path, GuardrailPolicy())
    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "sensitive_file"
```

- [ ] **Step 2: Write failing write-policy tests**

Test automatic source write, approval for tests, and rejection for delete actions.

- [ ] **Step 3: Run red verification**

Run: `python -m pytest tests/test_guardrails.py -q`

Expected: FAIL because `pyrepair.guardrails` does not exist.

- [ ] **Step 4: Implement guardrail policy**

Implement:

- project-root containment with resolved paths;
- sensitive filename pattern rejection;
- automatic allow for `.py` files outside test paths;
- approval required for test files, config files, dependency files, docs, CI files, and lock files;
- reject for file deletion and writes outside project;
- allow only configured pytest command for `RUN_TESTS`.

- [ ] **Step 5: Run green verification**

Run: `python -m pytest tests/test_guardrails.py -q`

Expected: PASS.

- [ ] **Step 6: Commit and record evidence**

Run:

```bash
git add src/pyrepair/guardrails.py tests/test_guardrails.py PLAN.md AGENT_LOG.md
git commit -m "feat: add deterministic guardrails"
```

Update `PLAN.md` Task 5 status and `AGENT_LOG.md` with the commit hash.

---

### Task 6: Pytest Feedback Parser

**Status:** Complete; implementation commit `3d96df8`, evidence commit `aeade5a`.

**Files:**
- Create: `src/pyrepair/feedback.py`
- Create: `tests/test_feedback.py`

**Interfaces:**
- Consumes `TestResult`, `FailureSummary`, `FailureCategory`.
- Produces `parse_pytest_feedback(test_result: TestResult) -> FailureSummary`.

- [x] **Step 1: Write failing assertion parser test**

Use a pytest output fixture containing `E       assert 4 == 3` and a failed test path. Assert category `ASSERTION_FAILURE`, failed test name, and related file extraction.

- [x] **Step 2: Write failing exception/import/syntax/timeout tests**

Use bounded string fixtures for:

- `ModuleNotFoundError`;
- `SyntaxError`;
- traceback with `ValueError`;
- `timed_out=True`.

- [x] **Step 3: Run red verification**

Run: `python -m pytest tests/test_feedback.py -q`

Expected: FAIL because `pyrepair.feedback` does not exist.

- [x] **Step 4: Implement parser**

Implement conservative parsing:

- if `timed_out` is true, return `TIMEOUT`;
- if output contains `SyntaxError`, return `SYNTAX_ERROR`;
- if output contains `ImportError` or `ModuleNotFoundError`, return `IMPORT_ERROR`;
- if output contains assertion markers such as `E       assert`, return `ASSERTION_FAILURE`;
- if output contains `Traceback`, return `RUNTIME_EXCEPTION`;
- otherwise return `UNKNOWN_FAILURE`.

- [x] **Step 5: Run green verification**

Run: `python -m pytest tests/test_feedback.py -q`

Expected: PASS.

- [x] **Step 6: Commit and record evidence**

Run:

```bash
git add src/pyrepair/feedback.py tests/test_feedback.py PLAN.md AGENT_LOG.md
git commit -m "feat: classify pytest feedback"
```

Update `PLAN.md` Task 6 status and `AGENT_LOG.md` with the commit hash.

---

### Task 7: Tool Implementations and Fixture Project

**Status:** Complete; implementation commit `223f5d2`, evidence commit `edad19f`.

**Files:**
- Create: `src/pyrepair/tools.py`
- Create: `tests/test_tools.py`
- Create: `examples/buggy_calculator/src/calculator.py`
- Create: `examples/buggy_calculator/tests/test_calculator.py`

**Interfaces:**
- Produces `ProjectScanner.scan(project_root: Path) -> dict`.
- Produces `PytestRunner.run(project_root: Path, command: list[str], timeout_seconds: int) -> TestResult`.
- Produces `SafeFileReader.read(project_root: Path, path: str) -> str`.
- Produces `PatchApplier.apply_unified_diff(project_root: Path, diff_text: str) -> PatchRecord`.

- [x] **Step 1: Write failing project scanner tests**

Create a temp project with `src/app.py` and `tests/test_app.py`. Assert scanner separates source and test files.

- [x] **Step 2: Write failing pytest runner tests**

Create a temp pytest project with one failing test. Run `PytestRunner` and assert non-zero exit code and captured output.

- [x] **Step 3: Write failing file reader and patch tests**

Assert safe reader reads project files and patch applier changes a source file when given a unified diff.

- [x] **Step 4: Run red verification**

Run: `python -m pytest tests/test_tools.py -q`

Expected: FAIL because `pyrepair.tools` does not exist.

- [x] **Step 5: Add fixture project**

Create `examples/buggy_calculator` with a deliberately failing implementation:

- `add(1, 2)` returns an incorrect result before repair;
- `tests/test_calculator.py` expects correct arithmetic.

- [x] **Step 6: Implement tools**

Implement scanner, pytest runner, safe reader, and patch applier. All write operations must assume guardrails already approved the action, but patch applier must still refuse paths outside the project.

- [x] **Step 7: Run green verification**

Run: `python -m pytest tests/test_tools.py -q`

Expected: PASS.

- [x] **Step 8: Commit and record evidence**

Run:

```bash
git add src/pyrepair/tools.py tests/test_tools.py examples/buggy_calculator PLAN.md AGENT_LOG.md
git commit -m "feat: add project tools and buggy fixture"
```

Update `PLAN.md` Task 7 status and `AGENT_LOG.md` with the commit hash.

---

### Task 8: Run Store

**Status:** Complete; implementation commit `68893fb`, evidence commit `9f0acdd`.

**Files:**
- Create: `src/pyrepair/store.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Consumes `RunRecord`, `RunStep`, and related models.
- Produces `JsonlRunStore`.
- Methods:
  - `create_run(run: RunRecord) -> None`
  - `append_step(run_id: str, step: RunStep) -> None`
  - `get_run(run_id: str) -> RunRecord`
  - `list_runs() -> list[RunRecord]`

- [x] **Step 1: Write failing run store tests**

Test that a run can be created, a step appended, and the run loaded from disk.

- [x] **Step 2: Run red verification**

Run: `python -m pytest tests/test_store.py -q`

Expected: FAIL because `pyrepair.store` does not exist.

- [x] **Step 3: Implement append-only JSONL store**

Store one JSONL file per run under a configurable run directory. Serialize dataclasses and enums into JSON-safe dicts. Never store API keys.

- [x] **Step 4: Run green verification**

Run: `python -m pytest tests/test_store.py -q`

Expected: PASS.

- [x] **Step 5: Commit and record evidence**

Run:

```bash
git add src/pyrepair/store.py tests/test_store.py PLAN.md AGENT_LOG.md
git commit -m "feat: add append-only run store"
```

Update `PLAN.md` Task 8 status and `AGENT_LOG.md` with the commit hash.

---

### Task 9: LLM Clients and Mock Scripts

**Status:** Complete; implementation commit `9e71f2e`, evidence commit
`221e557`. Review-fix commit `6b0c882`; review-fix evidence commit `9397bd5`.

**Files:**
- Create: `src/pyrepair/llm.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Produces protocol/base class `LLMClient` with `generate(messages: list[dict[str, str]]) -> str`.
- Produces `MockLLMClient(script: list[str])`.
- Produces `OpenAICompatibleLLMClient(base_url: str, model: str, api_key: str)`.

- [x] **Step 1: Write failing mock LLM tests**

Assert `MockLLMClient` returns scripted responses in order and raises a clear error when exhausted.

- [x] **Step 2: Write failing OpenAI-compatible request-shape test**

Use monkeypatching or a fake HTTP transport. Assert the client sends `model`, `messages`, and `Authorization: Bearer <key>` to `/chat/completions` or the configured compatible endpoint. Do not call the network.

- [x] **Step 3: Run red verification**

Run: `python -m pytest tests/test_llm.py -q`

Expected: FAIL because `pyrepair.llm` does not exist.

- [x] **Step 4: Implement clients**

Implement mock client and OpenAI-compatible client. Add timeout handling and response-shape errors. Do not log API keys.

- [x] **Step 5: Run green verification**

Run: `python -m pytest tests/test_llm.py -q`

Expected: PASS.

- [x] **Step 6: Commit and record evidence**

Run:

```bash
git add src/pyrepair/llm.py tests/test_llm.py PLAN.md AGENT_LOG.md
git commit -m "feat: add injectable LLM clients"
```

Update `PLAN.md` Task 9 status and `AGENT_LOG.md` with the commit hash.

---

### Task 10: Agent Core Loop and Mock Feedback Demo

**Status:** Complete; implementation commit `2593c8c`, evidence commit
`df062a2`. TDD red verification failed as expected because
`pyrepair.core` was absent; focused green verification passed `2 passed`.
`make test` is unavailable in this Windows environment (`make` is not
recognized), and the equivalent `python -m pytest -q` verification passed
`85 passed`. Review-fix commit `7c1d920`; review-fix evidence commit
`6d87f15`. `conftest.py` now requires approval before patching, and JSONL
replay persists final run status. Focused review verification passed
`44 passed`; full verification passed `87 passed`.

**Files:**
- Create: `src/pyrepair/core.py`
- Create: `tests/test_core_loop.py`

**Interfaces:**
- Consumes `LLMClient`, `parse_action`, `evaluate_action`, tools, feedback parser, and run store.
- Produces `AgentCoreLoop.run(project_root: Path, config: RepairConfig) -> RunRecord`.
- Produces stop policy inside core or as a focused helper.

- [x] **Step 1: Write failing feedback-loop test**

Use a temp copy of `examples/buggy_calculator`. Script mock LLM responses:

1. `READ_FILE` for `src/calculator.py`;
2. `APPLY_PATCH` with a deliberately wrong source patch;
3. `APPLY_PATCH` with the correct source patch after assertion feedback.

Assert:

- initial pytest fails;
- at least one step has category `ASSERTION_FAILURE`;
- final run status is passed;
- final source file contains the correct implementation;
- run store has multiple steps.

- [x] **Step 2: Write failing guardrail-loop test**

Script mock LLM response that attempts `APPLY_PATCH` on `tests/test_calculator.py`. Assert final status is `waiting_approval` and no test file is changed.

- [x] **Step 3: Run red verification**

Run: `python -m pytest tests/test_core_loop.py -q`

Expected: FAIL because `pyrepair.core` does not exist.

- [x] **Step 4: Implement core loop**

Implement:

- initial project scan;
- initial pytest run;
- context construction;
- LLM call;
- action parsing;
- guardrail evaluation;
- tool dispatch;
- feedback parsing after test runs;
- step persistence;
- stop conditions.

- [x] **Step 5: Run green verification**

Run: `python -m pytest tests/test_core_loop.py -q`

Expected: PASS.

- [x] **Step 6: Run related tests**

Run: `make test`

Expected: PASS.

- [x] **Step 7: Commit and record evidence**

Run:

```bash
git add src/pyrepair/core.py tests/test_core_loop.py PLAN.md AGENT_LOG.md
git commit -m "feat: add agent core feedback loop"
```

Update `PLAN.md` Task 10 status and `AGENT_LOG.md` with the commit hash.

---

### Task 11: Run Controller, Configuration, and CLI

**Status:** Complete; implementation commit `7137cac`, evidence commit
`522befc`. TDD red verification failed because
`pyrepair.config` and `pyrepair.cli` were absent; focused green verification
passed `4 passed`. `make test` is unavailable in this Windows environment, and
the equivalent `python -m pytest -q` verification passed `91 passed`.
Review fix: unconfigured `OPENAI_COMPATIBLE` runs now fail explicitly instead
of silently using mock; focused review verification passed `5 passed`, and full
verification passed `92 passed`. Review-fix commit `435494a`.
Review-fix evidence commit `0c4cf48`.

**Files:**
- Create: `src/pyrepair/config.py`
- Create: `src/pyrepair/run_controller.py`
- Create: `src/pyrepair/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces `RepairConfig` dataclass.
- Produces `RunController.start_run(project_root: Path, config: RepairConfig) -> RunRecord`.
- Produces Typer CLI entrypoint `pyrepair`.

- [x] **Step 1: Write failing config tests**

Assert defaults:

- max rounds is 3 for demo mode;
- pytest command is `python -m pytest`;
- timeout is positive;
- backend can be mock or openai-compatible.

- [x] **Step 2: Write failing CLI demo tests**

Use Typer test runner. Assert:

- `pyrepair demo feedback-loop` exits 0;
- output includes final status;
- `pyrepair demo guardrail` exits 0;
- output includes `approval_required` or equivalent guardrail status.

- [x] **Step 3: Run red verification**

Run: `python -m pytest tests/test_cli.py -q`

Expected: FAIL because CLI and controller do not exist.

- [x] **Step 4: Implement config, controller, and CLI**

Implement commands:

- `pyrepair run <project-path>`;
- `pyrepair demo feedback-loop`;
- `pyrepair demo guardrail`;
- `pyrepair demo full`;
- `pyrepair web` as a command that starts the WebUI after Task 13.

- [x] **Step 5: Add console script metadata**

Update `pyproject.toml` so `pyrepair` points to `pyrepair.cli:app`.

- [x] **Step 6: Run green verification**

Run: `python -m pytest tests/test_cli.py -q`

Expected: PASS.

- [x] **Step 7: Run full offline tests**

Run: `make test`

Expected: PASS.

- [x] **Step 8: Commit and record evidence**

Run:

```bash
git add src/pyrepair/config.py src/pyrepair/run_controller.py src/pyrepair/cli.py tests/test_cli.py pyproject.toml PLAN.md AGENT_LOG.md
git commit -m "feat: add run controller and CLI"
```

Update `PLAN.md` Task 11 status and `AGENT_LOG.md` with the commit hash.

---

### Task 12: Credential Management

**Status:** Complete; implementation commit `80f5363`, evidence commit
`6136891`. TDD red verification failed because
`pyrepair.credentials` was absent; focused green verification passed `8 passed`.
`make test` is unavailable in this Windows environment, and the equivalent
`python -m pytest -q` verification passed `95 passed`. Review fix: `key set`
no longer accepts command-line secrets and backend status failures are explicit;
focused review verification passed `11 passed`, and full verification passed
`98 passed`.

**Files:**
- Create: `src/pyrepair/credentials.py`
- Create: `tests/test_credentials.py`
- Modify: `src/pyrepair/cli.py`

**Interfaces:**
- Produces `CredentialStore`.
- Produces methods `set_key(provider: str, value: str)`, `get_key(provider: str)`, `clear_key(provider: str)`, `status(provider: str)`.
- CLI adds `pyrepair key set`, `pyrepair key status`, and `pyrepair key clear`.

- [x] **Step 1: Write failing credential tests**

Use a temp or fake backend. Assert:

- set stores a value;
- status reports configured without revealing the key;
- clear removes the value;
- redaction turns `sk-abcdef123456` into a non-secret display string.

- [x] **Step 2: Write failing CLI key tests**

Use Typer test runner with monkeypatched credential store. Assert `key status` does not print the secret.

- [x] **Step 3: Run red verification**

Run: `python -m pytest tests/test_credentials.py tests/test_cli.py -q`

Expected: FAIL because credential commands do not exist.

- [x] **Step 4: Implement credential store**

Use system keyring when available. Provide a test-only in-memory backend for deterministic tests. Ensure no test needs a real system keyring.

- [x] **Step 5: Implement CLI commands**

Implement hidden input for `key set`, non-secret output for `key status`, and deletion for `key clear`.

- [x] **Step 6: Run green verification**

Run: `python -m pytest tests/test_credentials.py tests/test_cli.py -q`

Expected: PASS.

- [x] **Step 7: Commit and record evidence**

Run:

```bash
git add src/pyrepair/credentials.py src/pyrepair/cli.py tests/test_credentials.py tests/test_cli.py PLAN.md AGENT_LOG.md
git commit -m "feat: add secure credential management"
```

Update `PLAN.md` Task 12 status and `AGENT_LOG.md` with the commit hash.

---

### Task 13: WebUI Operational Console

**Files:**
- Create: `src/pyrepair/web/__init__.py`
- Create: `src/pyrepair/web/app.py`
- Create: `src/pyrepair/web/static/app.js`
- Create: `src/pyrepair/web/static/styles.css`
- Create: `tests/test_web.py`
- Modify: `src/pyrepair/cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces FastAPI app factory `create_app(run_store: JsonlRunStore | None = None)`.
- Produces endpoints:
  - `GET /`
  - `GET /api/runs`
  - `GET /api/runs/{run_id}`
  - `POST /api/demo/feedback-loop`
  - `POST /api/demo/guardrail`

- [ ] **Step 1: Record Open Design decision**

Consult available Open Design guidance or note unavailability. Add the decision to `AGENT_LOG.md`. The WebUI must be an operational console with run timeline, failure summary, diff, and guardrail sections.

- [ ] **Step 2: Write failing WebUI API tests**

Use FastAPI test client. Assert:

- `GET /` returns 200 and contains "PyRepair Agent";
- `POST /api/demo/guardrail` returns a run with waiting approval status;
- `GET /api/runs` returns JSON list.

- [ ] **Step 3: Run red verification**

Run: `python -m pytest tests/test_web.py -q`

Expected: FAIL because web app does not exist.

- [ ] **Step 4: Implement WebUI app**

Implement mock/demo-only endpoints first. Serve simple HTML and static assets. Do not expose arbitrary host paths in public demo endpoints.

- [ ] **Step 5: Wire `pyrepair web`**

Update CLI to start the FastAPI app with localhost binding by default.

- [ ] **Step 6: Run green verification**

Run: `python -m pytest tests/test_web.py tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 7: Run full offline tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 8: Commit and record evidence**

Run:

```bash
git add src/pyrepair/web src/pyrepair/cli.py tests/test_web.py pyproject.toml PLAN.md AGENT_LOG.md
git commit -m "feat: add WebUI operational console"
```

Update `PLAN.md` Task 13 status and `AGENT_LOG.md` with the commit hash.

---

### Task 14: CI, Docker, README, and Final Process Docs

**Files:**
- Create: `.github/workflows/unit-test.yml`
- Create: `.gitlab-ci.yml`
- Create: `Dockerfile`
- Create: `README.md`
- Create: `REFLECTION.md`
- Modify: `SPEC_PROCESS.md`
- Modify: `AGENT_LOG.md`
- Modify: `PLAN.md`

**Interfaces:**
- Produces CI that runs `make test`.
- Produces Docker image that can run mock demos.
- Produces README sections required by the course.

- [ ] **Step 1: Write failing CI presence test**

Add a test in `tests/test_project_files.py` asserting:

- `.github/workflows/unit-test.yml` exists;
- `.gitlab-ci.yml` exists;
- `.gitlab-ci.yml` contains `unit-test`;
- `Dockerfile` exists;
- `README.md` contains installation, running, distribution, key setup, known limits, and safety boundaries headings.

- [ ] **Step 2: Run red verification**

Run: `python -m pytest tests/test_project_files.py -q`

Expected: FAIL because required files do not exist.

- [ ] **Step 3: Add GitHub Actions workflow**

Create workflow that checks out code, sets up Python, installs package with dev dependencies, and runs `make test`.

- [ ] **Step 4: Add GitLab CI**

Create `.gitlab-ci.yml` with a job named `unit-test` that runs the same offline test command.

- [ ] **Step 5: Add Dockerfile**

Create Dockerfile that installs the package and defaults to a command that can run mock demo or WebUI mock/demo-only mode.

- [ ] **Step 6: Write README**

Include:

- project introduction;
- installation;
- running CLI;
- running WebUI;
- demo commands;
- distribution commands;
- Docker build/run;
- directory structure;
- secure key configuration;
- `.env` risk warning;
- safety boundaries;
- known limitations;
- CI commands.

- [ ] **Step 7: Prepare REFLECTION skeleton**

Create `REFLECTION.md` with headings from the course requirements. Leave no fake reflection text before implementation evidence exists. Use neutral section prompts that the student will complete at the end.

- [ ] **Step 8: Run green verification**

Run: `python -m pytest tests/test_project_files.py -q`

Expected: PASS.

- [ ] **Step 9: Run full offline tests**

Run: `make test`

Expected: PASS.

- [ ] **Step 10: Commit and record evidence**

Run:

```bash
git add .github/workflows/unit-test.yml .gitlab-ci.yml Dockerfile README.md REFLECTION.md tests/test_project_files.py SPEC_PROCESS.md PLAN.md AGENT_LOG.md
git commit -m "chore: add CI distribution and final docs"
```

Update `PLAN.md` Task 14 status and `AGENT_LOG.md` with the commit hash.

---

## Post-Implementation Review Gates

- [ ] Run `make test` and record output in `AGENT_LOG.md`.
- [ ] Run `pyrepair demo feedback-loop` and record output in `AGENT_LOG.md`.
- [ ] Run `pyrepair demo guardrail` and record output in `AGENT_LOG.md`.
- [ ] Run the real API smoke test only if the human owner has configured an API key and explicitly approves the call.
- [ ] Push feature branches and collect PR/MR links.
- [ ] Ensure GitHub Actions has a passing run.
- [ ] Ensure `.gitlab-ci.yml` has a `unit-test` job and collect final pass evidence on the required platform if available.
- [ ] Build Docker image and run mock demo inside it.
- [ ] Deploy mock/demo-only WebUI and record the public URL.
- [ ] Complete `REFLECTION.md` manually as the student owner.
- [ ] Run final secret scan over source, docs, logs, and history before submission.

## Plan Self-Review Checklist

- SPEC coverage: Tasks cover harness loop, tools, feedback, guardrails, memory/store, config, credentials, CLI, WebUI, mock demos, CI, distribution, deployment, process evidence, cold-start validation, and PR/worktree evidence.
- Completion-marker scan: This plan must not contain unfinished markers or unspecified implementation steps.
- Type consistency: Later tasks rely on names introduced earlier: `Action`, `ActionType`, `FailureSummary`, `GuardrailDecision`, `TestResult`, `JsonlRunStore`, `LLMClient`, `AgentCoreLoop`, `RepairConfig`, and `RunController`.
- TDD: Each implementation task starts with failing tests and records the expected red/green command.
