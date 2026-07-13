from __future__ import annotations

import json

import pytest

from pyrepair.llm import (
    LLMResponseError,
    LLMTimeoutError,
    MockLLMClient,
    OpenAICompatibleLLMClient,
)


def test_mock_client_returns_scripted_responses_in_order() -> None:
    client = MockLLMClient(["first response", "second response"])

    assert client.generate([]) == "first response"
    assert client.generate([]) == "second response"


def test_mock_client_raises_clear_error_when_script_is_exhausted() -> None:
    client = MockLLMClient([])

    with pytest.raises(RuntimeError, match="script exhausted"):
        client.generate([])


def test_openai_compatible_client_sends_expected_request_shape() -> None:
    captured: dict[str, object] = {}

    def fake_transport(
        url: str,
        body: bytes,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> bytes:
        captured.update(
            url=url,
            body=json.loads(body),
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        return b'{"choices":[{"message":{"content":"repair action"}}]}'

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example/v1/",
        model="repair-model",
        api_key="test-api-key",
        transport=fake_transport,
        timeout_seconds=12.5,
    )
    messages = [{"role": "user", "content": "Fix the test."}]

    assert client.generate(messages) == "repair action"
    assert captured == {
        "url": "https://llm.example/v1/chat/completions",
        "body": {"model": "repair-model", "messages": messages},
        "headers": {
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json",
        },
        "timeout_seconds": 12.5,
    }


def test_openai_compatible_client_wraps_transport_timeouts_without_key() -> None:
    api_key = "test-api-key"

    def timeout_transport(
        url: str,
        body: bytes,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> bytes:
        raise TimeoutError("transport timed out")

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example",
        model="repair-model",
        api_key=api_key,
        transport=timeout_transport,
    )

    with pytest.raises(LLMTimeoutError) as error:
        client.generate([])

    assert api_key not in str(error.value)


def test_openai_compatible_client_rejects_invalid_response_shape_without_key() -> None:
    api_key = "test-api-key"

    def invalid_response_transport(
        url: str,
        body: bytes,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> bytes:
        return b'{"choices":[]}'

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example",
        model="repair-model",
        api_key=api_key,
        transport=invalid_response_transport,
    )

    with pytest.raises(LLMResponseError, match="response") as error:
        client.generate([])

    assert api_key not in str(error.value)
