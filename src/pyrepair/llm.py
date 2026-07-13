from __future__ import annotations

import json
import socket
from collections.abc import Callable
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


Message = dict[str, str]
Transport = Callable[[str, bytes, dict[str, str], float], bytes]


class LLMClient(Protocol):
    def generate(self, messages: list[Message]) -> str:
        """Generate a completion for chat messages."""


class LLMTimeoutError(RuntimeError):
    """Raised when an LLM request exceeds its configured timeout."""


class LLMResponseError(RuntimeError):
    """Raised when an LLM response cannot be decoded as a chat completion."""


class MockLLMClient:
    def __init__(self, script: list[str]) -> None:
        self._script = list(script)
        self._next_response = 0

    def generate(self, messages: list[Message]) -> str:
        if self._next_response >= len(self._script):
            raise RuntimeError("Mock LLM script exhausted")
        response = self._script[self._next_response]
        self._next_response += 1
        return response


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        *,
        transport: Transport | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._transport = transport or _default_transport
        self._timeout_seconds = timeout_seconds

    def generate(self, messages: list[Message]) -> str:
        body = json.dumps({"model": self._model, "messages": messages}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response_bytes = self._transport(
                f"{self._base_url}/chat/completions",
                body,
                headers,
                self._timeout_seconds,
            )
        except (TimeoutError, socket.timeout) as error:
            raise LLMTimeoutError("LLM request timed out") from error
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise LLMTimeoutError("LLM request timed out") from error
            raise RuntimeError("LLM request failed") from error

        return _extract_content(response_bytes)


def _default_transport(
    url: str,
    body: bytes,
    headers: dict[str, str],
    timeout_seconds: float,
) -> bytes:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _extract_content(response_bytes: bytes) -> str:
    try:
        response = json.loads(response_bytes)
        content = response["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LLMResponseError("LLM response has an invalid chat completion shape") from error
    if not isinstance(content, str):
        raise LLMResponseError("LLM response has an invalid chat completion shape")
    return content
