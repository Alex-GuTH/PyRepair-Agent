import pytest

from pyrepair.actions import ActionParseError, parse_action
from pyrepair.models import ActionParseStatus, ActionType


def test_parse_valid_read_file_action():
    raw = '{"type":"READ_FILE","payload":{"path":"src/app.py"}}'

    action = parse_action(raw)

    assert action.type is ActionType.READ_FILE
    assert action.payload == {"path": "src/app.py"}
    assert action.raw_model_output == raw
    assert action.parse_status is ActionParseStatus.PARSED


def test_rejects_malformed_json():
    with pytest.raises(ActionParseError):
        parse_action('{"type":"READ_FILE","payload":')


def test_rejects_non_object_top_level_json():
    with pytest.raises(ActionParseError):
        parse_action('[]')


def test_rejects_missing_action_type():
    with pytest.raises(ActionParseError):
        parse_action('{"payload":{"path":"src/app.py"}}')


def test_rejects_unknown_action_type():
    with pytest.raises(ActionParseError):
        parse_action('{"type":"SHELL","payload":{"command":"rm -rf ."}}')


def test_rejects_missing_payload():
    with pytest.raises(ActionParseError):
        parse_action('{"type":"READ_FILE"}')


def test_rejects_non_object_payload():
    with pytest.raises(ActionParseError):
        parse_action('{"type":"READ_FILE","payload":[]}')
