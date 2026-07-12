from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum


class ActionType(str, Enum):
    PROJECT_SCAN = "PROJECT_SCAN"
    RUN_TESTS = "RUN_TESTS"
    READ_FILE = "READ_FILE"
    APPLY_PATCH = "APPLY_PATCH"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    FINISH = "FINISH"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    CANCELLED = "CANCELLED"


class GuardrailDecisionType(str, Enum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class FailureCategory(str, Enum):
    NONE = "NONE"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    RUNTIME_EXCEPTION = "RUNTIME_EXCEPTION"
    IMPORT_ERROR = "IMPORT_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    COLLECTION_ERROR = "COLLECTION_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class TestStatus(str, Enum):
    __test__ = False

    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class LLMProvider(str, Enum):
    MOCK = "MOCK"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"


class ActionParseStatus(str, Enum):
    PARSED = "PARSED"
    INVALID_JSON = "INVALID_JSON"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"


@dataclass
class Action:
    type: ActionType
    payload: dict[str, object] = field(default_factory=dict)
    raw_model_output: str = ""
    parse_status: ActionParseStatus = ActionParseStatus.PARSED


@dataclass
class GuardrailDecision:
    decision: GuardrailDecisionType
    policy_code: str = ""
    reason: str = ""
    risk_level: str = "low"


@dataclass
class FailureSummary:
    status: TestStatus = TestStatus.FAILED
    category: FailureCategory = FailureCategory.UNKNOWN_FAILURE
    failed_tests: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    traceback_excerpt: str = ""
    line_hints: list[int] = field(default_factory=list)
    message: str = ""


@dataclass
class TestResult:
    __test__ = False

    command: list[str] = field(default_factory=list)
    exit_code: int = 0
    duration_ms: int = 0
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    raw_output_ref: str = ""
    failure_summary: FailureSummary | None = None


@dataclass
class PatchRecord:
    files_changed: list[str] = field(default_factory=list)
    diff: str = ""
    applied: bool = False
    requires_approval: bool = False
    source_step: int | None = None


@dataclass
class ToolResult:
    tool_name: str
    success: bool = False
    stdout_summary: str = ""
    stderr_summary: str = ""
    exit_code: int | None = None
    changed_files: list[str] = field(default_factory=list)
    error: str = ""
    test_result: TestResult | None = None
    patch_record: PatchRecord | None = None


@dataclass
class RunStep:
    run_id: str
    round_index: int
    llm_backend: str = ""
    context_summary: str = ""
    action: Action | None = None
    guardrail_decision: GuardrailDecision | None = None
    tool_result: ToolResult | None = None
    feedback: FailureSummary | None = None
    created_at: str = ""


@dataclass
class RunRecord:
    id: str
    project_root: str
    status: RunStatus = RunStatus.RUNNING
    created_at: str = ""
    updated_at: str = ""
    max_rounds: int = 3
    current_round: int = 0
    steps: list[RunStep] = field(default_factory=list)
    final_summary: str = ""


@dataclass
class ApprovalRequest:
    id: str
    run_id: str
    step_id: str = ""
    action: Action | None = None
    reason: str = ""
    diff: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_note: str = ""


@dataclass
class LLMConfig:
    provider: LLMProvider = LLMProvider.MOCK
    base_url: str = ""
    model: str = ""
    api_key_ref: str = ""
    timeout_seconds: int = 60
    max_output_tokens: int = 2048


def to_jsonable(value: object) -> object:
    """Convert enums and nested dataclasses into JSON-compatible values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


def dataclass_to_dict(value: object) -> dict[str, object]:
    """Serialize a dataclass and all nested values into a JSON-compatible dict."""
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError("value must be a dataclass instance")
    serialized = to_jsonable(value)
    if not isinstance(serialized, dict):
        raise TypeError("dataclass serialization must produce a dictionary")
    return serialized
