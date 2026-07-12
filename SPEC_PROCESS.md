# PyRepair Agent SPEC Process

Status: in progress
Date: 2026-07-12

## 1. Brainstorming Summary

This document records the Superpowers brainstorming and planning process for
PyRepair Agent, an AI4SE Final Project A Coding Agent Harness.

The project began with the broad goal of building a coding agent harness that
could satisfy the course requirements: Superpowers workflow, SPEC/PLAN first,
TDD, mock LLM unit tests, mechanism demos, process evidence, distribution, CI,
WebUI, and optional real API access.

Three candidate directions were considered:

1. Test-Repair Coding Agent.
2. Policy-Governed Coding Agent.
3. Project-Memory Coding Agent.

The selected direction was Test-Repair Coding Agent because it provides a clear
coding-domain feedback signal through pytest and makes the main harness
mechanism easy to test deterministically with a mock LLM.

## 2. Key Brainstorming Iterations

### Iteration 1: Project Direction

Question asked:

> Which of the three single-person Coding Agent Harness directions should become
> the project?

Human decision:

> Direction 1: Test-Repair Coding Agent.

Effect on design:

- The main contribution became a pytest feedback loop.
- The project scope became Python + pytest rather than a general coding agent.
- Mock LLM tests became straightforward because repair rounds can be scripted.

### Iteration 2: Target Ecosystem

Question asked:

> Should the first version target Python, Java/Maven, or TypeScript/Node?

Human decision:

> Python + pytest.

Effect on design:

- Python was selected for both the target repair domain and the harness
  implementation language.
- pytest output became the objective feedback signal.
- The test fixture strategy became small local pytest projects.

### Iteration 3: Interaction Model

Question asked:

> Should the project be CLI-first, WebUI-first, or WebUI-only?

Human decision:

> CLI-first plus a simple WebUI console.

Effect on design:

- CLI became the primary local repair interface.
- WebUI became an operational console for run visualization, diff inspection,
  guardrail events, and mock/demo-only public deployment.
- The design avoided a heavy frontend framework so the harness mechanisms remain
  the focus.

### Iteration 4: Real API Access

Question asked:

> Should the real LLM backend support OpenAI-compatible APIs, only OpenAI, or
> mock-only mode?

Human decision:

> OpenAI-compatible API plus mock LLM backend.

Effect on design:

- The user only needs to provide an API key, model, and optionally base URL.
- The implementation can support OpenAI and other compatible providers without
  changing the harness core.
- Mock LLM remains the default for tests and demos.

### Iteration 5: Write Policy

Question asked:

> Which files may the agent modify automatically?

Human decision:

> Only ordinary Python source files; do not modify tests by default.

Effect on design:

- Test modification became a guarded action requiring human approval.
- The guardrail engine became a visible secondary contribution.
- The project avoids passing tests by weakening tests.

## 3. Accepted AI Suggestions

- Use Python + pytest as the first target ecosystem.
- Make feedback-loop engineering the main contribution.
- Keep governance guardrails as the secondary contribution.
- Use mock LLM plus OpenAI-compatible real backend.
- Use CLI as the primary interface and WebUI as an operational console.
- Provide both GitHub Actions and `.gitlab-ci.yml` because the course files
  mention both.
- Make the public WebUI mock/demo-only to avoid exposing local shell and file
  access.

## 4. Rejected or Revised AI Suggestions

- A broader multi-language coding agent was rejected as too risky for a
  single-person course project.
- A WebUI-first product was rejected because it would shift effort away from the
  harness mechanisms.
- Automatic test modification was rejected as a default behavior because it
  weakens the test suite as an objective feedback signal.
- Complex long-term memory was deferred because it risks turning into prompt
  engineering rather than deterministic code mechanisms.

## 5. Cold-Start Validation

Status: completed once; SPEC and PLAN revised.

Validation setup:

- A separate worker agent was spawned without conversation context.
- It was instructed to read only `SPEC.md` and `PLAN.md`.
- It was asked to attempt PLAN Task 3 or report ambiguities.

Findings:

- The cold-start agent could understand Task 3's intent but could not implement
  it unambiguously from `SPEC.md` and `PLAN.md`.
- It reported that enum members and values were not fully specified.
- It reported that dataclass fields, required fields, defaults, and nested model
  relationships were not explicit enough.
- It reported that fields such as `parse_status`, `status`, and `provider` had
  unclear allowed values.
- It did not modify files, run tests, or commit.

Required SPEC/PLAN revisions:

- `SPEC.md` was revised to define all model enums, dataclass fields, defaults,
  nested relationships, and serialization rules.
- `PLAN.md` Task 3 was revised to include the exact model contract and stronger
  tests for enum values, defaults, nested `TestResult.failure_summary`, and
  serialization.

## 6. Notes for Final Reflection

- SPEC quality improved when the course requirements were checked explicitly
  against the design.
- The Git repository state became a process risk: implementation should begin
  only after a valid repository exists, otherwise commit/worktree/PR evidence
  cannot be collected naturally.
- The project intentionally separates local repair mode from public demo mode to
  reduce remote code execution risk.

## 7. Task 1 Implementation Evidence

- The package import contract was written and run before the package existed;
  the expected `ModuleNotFoundError` confirmed the red phase.
- The minimal `src/pyrepair` package, project metadata, and canonical `make test`
  target were then added without introducing runtime dependencies.
- Green verification is recorded in `.superpowers/sdd/task-1-report.md`.
- Task 1 commit: `ccb8bd5`.
- Local `make test` could not run because Make is unavailable on this Windows
  environment; the underlying `python -m pytest -q` command passed and CI must
  validate `make test`.
