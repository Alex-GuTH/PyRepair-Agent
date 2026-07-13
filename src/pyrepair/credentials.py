"""Credential storage with optional system-keyring integration."""

from __future__ import annotations

import importlib
from typing import Protocol


_SERVICE_NAME = "pyrepair"


class CredentialBackend(Protocol):
    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class CredentialBackendUnavailable(RuntimeError):
    """Raised when a system credential backend cannot be used."""


class InMemoryCredentialBackend:
    """Deterministic credential backend for tests and injected local use."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._values[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._values.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        self._values.pop((service_name, username), None)


class UnavailableCredentialBackend:
    """Makes optional-keyring failures explicit without falling back to disk."""

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise CredentialBackendUnavailable("System keyring support is unavailable.")

    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def delete_password(self, service_name: str, username: str) -> None:
        raise CredentialBackendUnavailable("System keyring support is unavailable.")


class CredentialStore:
    """Store provider keys outside project configuration files."""

    def __init__(self, backend: CredentialBackend | None = None) -> None:
        self._backend = backend or _system_backend()

    def set_key(self, provider: str, value: str) -> None:
        self._backend.set_password(_SERVICE_NAME, _provider_name(provider), _key_value(value))

    def get_key(self, provider: str) -> str | None:
        return self._backend.get_password(_SERVICE_NAME, _provider_name(provider))

    def clear_key(self, provider: str) -> None:
        self._backend.delete_password(_SERVICE_NAME, _provider_name(provider))

    def status(self, provider: str) -> str:
        return "configured" if self.get_key(provider) else "not configured"


def redact_key(value: str) -> str:
    """Return a recognizable display value without returning the original key."""
    if not value:
        return "[REDACTED]"
    if len(value) <= 7:
        return "[REDACTED]"
    return f"{value[:3]}...{value[-4:]}"


def _system_backend() -> CredentialBackend:
    try:
        return importlib.import_module("keyring")
    except ImportError:
        return UnavailableCredentialBackend()


def _provider_name(provider: str) -> str:
    normalized = provider.strip()
    if not normalized:
        raise ValueError("Provider must not be empty.")
    return normalized


def _key_value(value: str) -> str:
    if not value:
        raise ValueError("API key must not be empty.")
    return value
