"""FastAPI application for the demo-only PyRepair operational console."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from pyrepair.config import RepairConfig
from pyrepair.llm import MockLLMClient
from pyrepair.models import RunRecord, dataclass_to_dict
from pyrepair.run_controller import RunController
from pyrepair.store import JsonlRunStore


_STATIC_ROOT = Path(__file__).parent / "static"
_FIXTURE_ROOT = Path(__file__).parents[3] / "examples" / "buggy_calculator"


def create_app(run_store: JsonlRunStore | None = None) -> FastAPI:
    """Create a local console whose public actions run only bundled demos."""
    store = run_store or JsonlRunStore(Path(tempfile.mkdtemp(prefix="pyrepair-web-runs-")))
    app = FastAPI(title="PyRepair Agent")
    app.mount("/static", StaticFiles(directory=_STATIC_ROOT), name="static")

    @app.get("/", response_class=HTMLResponse)
    def console() -> str:
        return _console_html()

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, object]]:
        return [_public_run(record) for record in store.list_runs()]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        try:
            return _public_run(store.get_run(run_id))
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail="run not found") from None

    @app.post("/api/demo/feedback-loop")
    def feedback_loop_demo() -> dict[str, object]:
        return _public_run(_run_demo(store, _feedback_script()))

    @app.post("/api/demo/guardrail")
    def guardrail_demo() -> dict[str, object]:
        return _public_run(_run_demo(store, _guardrail_script()))

    return app


def _run_demo(store: JsonlRunStore, script: list[str]) -> RunRecord:
    with tempfile.TemporaryDirectory(prefix="pyrepair-web-demo-") as temp_dir:
        project_root = Path(temp_dir) / "buggy_calculator"
        shutil.copytree(_FIXTURE_ROOT, project_root)
        return RunController(MockLLMClient(script)).start_run(
            project_root,
            RepairConfig(run_store=store),
        )


def _public_run(record: RunRecord) -> dict[str, object]:
    payload = dataclass_to_dict(record)
    return _redact_demo_paths(payload, record.project_root)


def _redact_demo_paths(value: object, project_root: str) -> object:
    display_root = "demo/buggy_calculator"
    if isinstance(value, dict):
        return {key: _redact_demo_paths(item, project_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_demo_paths(item, project_root) for item in value]
    if isinstance(value, str):
        return value.replace(project_root, display_root)
    return value


def _feedback_script() -> list[str]:
    return [
        _action("READ_FILE", {"path": "src/calculator.py"}),
        _action(
            "APPLY_PATCH",
            {
                "path": "src/calculator.py",
                "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -2 +2 @@\n-    return left - right\n+    return left * right\n",
            },
        ),
        _action(
            "APPLY_PATCH",
            {
                "path": "src/calculator.py",
                "diff": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -2 +2 @@\n-    return left * right\n+    return left + right\n",
            },
        ),
    ]


def _guardrail_script() -> list[str]:
    return [
        _action(
            "APPLY_PATCH",
            {
                "path": "tests/test_calculator.py",
                "diff": "--- a/tests/test_calculator.py\n+++ b/tests/test_calculator.py\n@@ -10 +10 @@\n-    assert add(1, 2) == 3\n+    assert add(1, 2) == -1\n",
            },
        )
    ]


def _action(action_type: str, payload: dict[str, object]) -> str:
    return json.dumps({"type": action_type, "payload": payload})


def _console_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PyRepair Agent</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header class="topbar"><strong>PyRepair Agent</strong><span>Demo Operations Console</span></header>
  <main>
    <section class="run-controls" aria-label="Demo controls">
      <button data-demo="feedback-loop">Run feedback loop</button>
      <button class="warning" data-demo="guardrail">Run guardrail demo</button>
      <span id="run-status" role="status"></span>
    </section>
    <section class="run-list-section"><h1>Run Timeline</h1><ol id="run-list" class="run-list"></ol></section>
    <section class="detail-grid" aria-live="polite">
      <article><h2>Failure Summary</h2><pre id="failure-summary">Select a run to inspect its test feedback.</pre></article>
      <article><h2>Diff</h2><pre id="diff">No patch selected.</pre></article>
      <article><h2>Guardrails</h2><pre id="guardrails">No guardrail decision selected.</pre></article>
    </section>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>"""
