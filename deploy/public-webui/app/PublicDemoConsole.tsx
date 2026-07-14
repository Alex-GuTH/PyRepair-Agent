"use client";

import { useMemo, useState } from "react";

type DemoRun = {
  id: string;
  label: string;
  status: "PASSED" | "WAITING_APPROVAL";
  summary: string;
  feedback: string;
  diff: string;
  guardrails: string;
  steps: string[];
};

const demoRuns: Record<"feedback" | "guardrail", DemoRun> = {
  feedback: {
    id: "run-public-feedback-loop",
    label: "Feedback loop",
    status: "PASSED",
    summary: "Pytest passed after patch.",
    feedback:
      "ASSERTION_FAILURE -> read src/calculator.py -> wrong patch kept failing -> final patch changed subtraction into addition -> NONE",
    diff:
      "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -2 +2 @@\n-    return left * right\n+    return left + right",
    guardrails:
      "RUN_TESTS allowed\nREAD_FILE allowed for bundled fixture\nAPPLY_PATCH allowed for ordinary Python source file",
    steps: [
      "Initial pytest run fails on add(1, 2) == 3.",
      "Mock LLM reads src/calculator.py.",
      "First patch changes subtraction to multiplication and still fails.",
      "Second patch changes multiplication to addition.",
      "Final pytest run passes.",
    ],
  },
  guardrail: {
    id: "run-public-guardrail",
    label: "Guardrail stop",
    status: "WAITING_APPROVAL",
    summary: "This write targets a protected project file.",
    feedback:
      "ASSERTION_FAILURE -> model proposes editing tests/test_calculator.py -> approval required",
    diff:
      "--- a/tests/test_calculator.py\n+++ b/tests/test_calculator.py\n@@ -10 +10 @@\n-    assert add(1, 2) == 3\n+    assert add(1, 2) == -1",
    guardrails:
      "APPLY_PATCH to tests/test_calculator.py blocked with protected_write_approval_required\nNo test file was modified automatically",
    steps: [
      "Initial pytest run fails on bundled calculator fixture.",
      "Mock LLM proposes changing a test expectation.",
      "Guardrail classifies the test file as protected.",
      "Run stops at WAITING_APPROVAL.",
    ],
  },
};

export function PublicDemoConsole() {
  const [runs, setRuns] = useState<DemoRun[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedId) ?? runs[0] ?? null,
    [runs, selectedId],
  );

  function triggerDemo(kind: "feedback" | "guardrail") {
    const run = {
      ...demoRuns[kind],
      id: `${demoRuns[kind].id}-${runs.length + 1}`,
    };
    setRuns((current) => [run, ...current]);
    setSelectedId(run.id);
  }

  return (
    <main className="console-shell">
      <section className="topbar" aria-label="Project status">
        <div>
          <p className="eyebrow">AI4SE Coding Agent Harness</p>
          <h1>PyRepair Agent</h1>
        </div>
        <div className="status-strip" aria-label="Safety status">
          <span>mock-only</span>
          <span>source-write guardrails</span>
          <span>no host paths</span>
        </div>
      </section>

      <section className="toolbar" aria-label="Demo controls">
        <button onClick={() => triggerDemo("feedback")}>Run feedback loop</button>
        <button className="secondary" onClick={() => triggerDemo("guardrail")}>
          Run guardrail demo
        </button>
        <p role="status">
          {selectedRun
            ? `${selectedRun.label}: ${selectedRun.status}`
            : "No demo run selected"}
        </p>
      </section>

      <section className="workspace">
        <aside className="runs-panel" aria-label="Run timeline">
          <h2>Run Timeline</h2>
          {runs.length === 0 ? (
            <p className="empty-state">No demo runs yet.</p>
          ) : (
            <ol>
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    className={run.id === selectedRun?.id ? "run-item active" : "run-item"}
                    onClick={() => setSelectedId(run.id)}
                  >
                    <strong>{run.label}</strong>
                    <span>{run.status}</span>
                  </button>
                </li>
              ))}
            </ol>
          )}
        </aside>

        <section className="detail-panel" aria-live="polite">
          {selectedRun ? (
            <>
              <div className="summary-row">
                <div>
                  <p className="eyebrow">Selected run</p>
                  <h2>{selectedRun.id}</h2>
                </div>
                <span className={`badge ${selectedRun.status.toLowerCase()}`}>
                  {selectedRun.status}
                </span>
              </div>
              <p className="summary">{selectedRun.summary}</p>
              <div className="detail-grid">
                <article>
                  <h3>Failure Summary</h3>
                  <pre>{selectedRun.feedback}</pre>
                </article>
                <article>
                  <h3>Diff</h3>
                  <pre>{selectedRun.diff}</pre>
                </article>
                <article>
                  <h3>Guardrails</h3>
                  <pre>{selectedRun.guardrails}</pre>
                </article>
                <article>
                  <h3>Steps</h3>
                  <ol className="steps">
                    {selectedRun.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </article>
              </div>
            </>
          ) : (
            <div className="empty-detail">
              <h2>Run a demo to inspect the harness timeline.</h2>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
