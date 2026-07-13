from pyrepair.guardrails import GuardrailPolicy, evaluate_action
from pyrepair.models import Action, ActionType, GuardrailDecisionType
import pytest


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


def test_allows_ordinary_python_source_write(tmp_path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": "src/repair.py"})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.ALLOW
    assert decision.policy_code == "source_write_allowed"


@pytest.mark.parametrize("path", ["generated/repair.py", "src/repair_generated.py"])
def test_requires_approval_for_generated_python_write(tmp_path, path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": path})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.APPROVAL_REQUIRED
    assert decision.policy_code == "protected_write_approval_required"


def test_rejects_binary_write(tmp_path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": "assets/logo.png"})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "binary_write_not_allowed"


@pytest.mark.parametrize("path", ["assets/firmware.bin", "assets/firmware"])
def test_rejects_unknown_or_binary_asset_write(tmp_path, path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": path})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "binary_write_not_allowed"


@pytest.mark.parametrize("path", ["assets/model.dat", "artifact.wasm"])
def test_rejects_unknown_extension_asset_write(tmp_path, path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": path})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "binary_write_not_allowed"


def test_requires_approval_for_extensionless_makefile_write(tmp_path):
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": "Makefile"})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.APPROVAL_REQUIRED
    assert decision.policy_code == "protected_write_approval_required"


@pytest.mark.parametrize("path", ["certs/service.crt", "certs/service.cer"])
@pytest.mark.parametrize("action_type", [ActionType.READ_FILE, ActionType.APPLY_PATCH])
def test_rejects_certificate_file_access(tmp_path, path, action_type):
    action = Action(type=action_type, payload={"path": path})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "sensitive_file"


def test_allows_source_write_when_project_root_is_named_tests(tmp_path):
    project_root = tmp_path / "tests"
    project_root.mkdir()
    action = Action(type=ActionType.APPLY_PATCH, payload={"path": "src/repair.py"})

    decision = evaluate_action(action, project_root, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.ALLOW


def test_requires_approval_for_test_write(tmp_path):
    action = Action(
        type=ActionType.APPLY_PATCH,
        payload={"files_changed": ["src/repair.py", "tests/test_repair.py"]},
    )

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.APPROVAL_REQUIRED
    assert decision.policy_code == "protected_write_approval_required"


def test_rejects_delete_action(tmp_path):
    action = Action(
        type=ActionType.APPLY_PATCH,
        payload={"path": "src/repair.py", "operation": "delete"},
    )

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "deletion_not_allowed"


def test_allows_configured_pytest_command_and_default(tmp_path):
    policy = GuardrailPolicy()
    configured_action = Action(
        type=ActionType.RUN_TESTS,
        payload={"command": list(policy.pytest_command)},
    )
    default_action = Action(type=ActionType.RUN_TESTS)

    assert evaluate_action(configured_action, tmp_path, policy).decision is GuardrailDecisionType.ALLOW
    assert evaluate_action(default_action, tmp_path, policy).decision is GuardrailDecisionType.ALLOW


def test_rejects_unconfigured_test_command(tmp_path):
    action = Action(type=ActionType.RUN_TESTS, payload={"command": ["pytest", "-q"]})

    decision = evaluate_action(action, tmp_path, GuardrailPolicy())

    assert decision.decision is GuardrailDecisionType.REJECT
    assert decision.policy_code == "test_command_mismatch"
