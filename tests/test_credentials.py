from __future__ import annotations

import pytest


def test_credential_store_sets_reports_and_clears_a_key() -> None:
    from pyrepair.credentials import CredentialStore, InMemoryCredentialBackend

    store = CredentialStore(InMemoryCredentialBackend())
    secret = "sk-test-only-credential-123456"

    store.set_key("openai", secret)

    assert store.get_key("openai") == secret
    assert store.status("openai") == "configured"
    assert secret not in store.status("openai")

    store.clear_key("openai")

    assert store.get_key("openai") is None
    assert store.status("openai") == "not configured"


def test_redact_key_never_returns_the_original_secret() -> None:
    from pyrepair.credentials import redact_key

    secret = "sk-abcdef123456"

    redacted = redact_key(secret)

    assert redacted != secret
    assert secret not in redacted
    assert redacted.startswith("sk-")


def test_credential_store_status_raises_when_backend_cannot_be_queried() -> None:
    from pyrepair.credentials import CredentialBackendUnavailable, CredentialStore

    class FailingBackend:
        def get_password(self, service_name: str, username: str) -> str | None:
            raise OSError("credential backend unavailable")

    store = CredentialStore(FailingBackend())

    with pytest.raises(CredentialBackendUnavailable, match="credential storage"):
        store.status("openai")
