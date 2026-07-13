"""Strict parsing for model-generated agent actions."""

import json

from pyrepair.models import Action, ActionType


class ActionParseError(ValueError):
    """Raised when model output cannot be parsed as an agent action."""


def parse_action(raw: str) -> Action:
    """Parse one JSON action emitted by the model."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as error:
        raise ActionParseError("invalid action JSON") from error

    if not isinstance(parsed, dict):
        raise ActionParseError("action JSON must be an object")
    if "type" not in parsed:
        raise ActionParseError("action type is required")
    if "payload" not in parsed:
        raise ActionParseError("action payload is required")

    try:
        action_type = ActionType(parsed["type"])
    except (TypeError, ValueError) as error:
        raise ActionParseError("unknown action type") from error

    payload = parsed["payload"]
    if not isinstance(payload, dict):
        raise ActionParseError("action payload must be an object")

    return Action(type=action_type, payload=payload, raw_model_output=raw)
