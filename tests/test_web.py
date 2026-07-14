from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from pyrepair.web.app import create_app


def test_operational_console_homepage_is_available() -> None:
    response = TestClient(create_app()).get("/")

    assert response.status_code == 200
    assert "PyRepair Agent" in response.text
    assert "Run Timeline" in response.text
    assert "Failure Summary" in response.text
    assert "Diff" in response.text
    assert "Guardrails" in response.text


def test_guardrail_demo_waits_for_approval() -> None:
    response = TestClient(create_app()).post("/api/demo/guardrail")

    assert response.status_code == 200
    assert response.json()["status"] == "WAITING_APPROVAL"


def test_demo_runs_are_listed_and_detail_is_available() -> None:
    client = TestClient(create_app())

    created = client.post("/api/demo/feedback-loop").json()
    response = client.get("/api/runs")
    detail = client.get(f"/api/runs/{created['id']}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["id"] == created["id"]
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]


def test_demo_api_does_not_expose_temporary_host_paths() -> None:
    response = TestClient(create_app()).post("/api/demo/feedback-loop")
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_root"] == "demo/buggy_calculator"
    assert str(Path.cwd()) not in response.text
    assert "pyrepair-web-demo-" not in response.text
