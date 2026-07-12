# PyRepair Agent SPEC

Status: draft for user review
Project type: AI4SE Final Project A, Coding Agent Harness
Date: 2026-07-12

## 1. Problem Statement

PyRepair Agent is a coding agent harness for small Python projects that use
pytest. A user provides a local project path. The agent runs pytest, parses the
failure, asks an LLM for the next structured action, executes allowed tools,
feeds objective test feedback back into the loop, and stops when tests pass, a
guardrail requires human approval, or a deterministic stop condition is reached.

The project is not meant to be a general IDE assistant or a wrapper around an
existing agent framework. Its purpose is to demonstrate the engineering layer of
a coding agent: main loop, tool dispatch, feedback, memory, guardrails,
configuration, credentials, distribution, CI, and process evidence.

The main contribution is a deterministic pytest feedback loop: pytest output is
classified and summarized by code, then used to drive multi-round repair. This
mechanism must remain testable when the real LLM is replaced by a mock LLM.

## 2. Goals and Non-Goals

### 2.1 Goals

- Support Python projects that use pytest.
- Provide a CLI-first repair workflow: `pyrepair run <project-path>`.
- Provide a WebUI console for run visualization, approval, and demonstration.
- Implement the agent main loop in this repository, without using a high-level
  agent orchestration framework.
- Provide two LLM backends:
  - a mock LLM backend for deterministic unit tests and mechanism demos;
  - an OpenAI-compatible backend for real API use.
- Automatically modify only ordinary Python source files by default.
- Require human approval before modifying tests, dependency files,
  configuration files, CI files, or any file outside the automatic write policy.
- Implement deterministic guardrails for file access, patch application,
  dangerous actions, and sensitive files.
- Store API keys securely and never print them in plaintext.
- Provide repeatable mock-LLM mechanism demos for feedback and guardrails.
- Provide CI, distribution documentation, process logs, PR/worktree evidence,
  and final pass evidence required by the course.

### 2.2 Non-Goals

- Supporting JavaScript, Java, C/C++, Rust, or multi-language repair in the
  first version.
- Automatically changing tests to make them pass.
- Automatically installing dependencies or editing lock files without human
  approval.
- Providing an IDE plugin.
- Providing arbitrary shell access to the LLM.
- Guaranteeing successful repair of large or complex real-world repositories.
- Building on LangChain AgentExecutor, AutoGen, CrewAI, LlamaIndex agents, or
  any other high-level agent loop.

## 3. Target Users

- Python developers with a small pytest project whose tests are failing.
- Students and reviewers who need to inspect how a coding agent harness works.
- AI4SE course staff who need deterministic evidence that the harness mechanisms
  work without depending on a real LLM.

## 4. User Stories

1. As a Python developer, I want to give the tool a local project path and have
   it run pytest automatically, so that I do not need to paste failure logs into
   an LLM manually.
2. As a developer, I want the agent to modify source files but not tests by
   default, so that passing tests remain a trustworthy acceptance signal.
3. As a developer, I want to inspect every repair round, failure classification,
   patch, and final diff, so that I can decide whether to keep the changes.
4. As a developer, I want dangerous actions to be blocked or paused for approval,
   so that the agent cannot read secrets, write outside the project, or damage my
   repository.
5. As a reviewer, I want a mock-LLM demo that always produces the same feedback
   loop, so that I can evaluate the harness without network access or API keys.
6. As a first-time user, I want to configure, update, and clear an API key
   safely, so that the key is not written into source code, logs, or terminal
   output.
7. As a presenter, I want a WebUI that shows run status, test feedback, diffs,
   and guardrail events, so that the system is understandable in a demo.

## 5. Domain and Mechanism Design

This section is required for the Coding Agent Harness track.

### 5.1 Actions and Tools

The LLM may only request structured actions. It cannot call the filesystem or
shell directly. Every action passes through the action parser, guardrail engine,
and tool dispatcher.

Initial action types:

- `PROJECT_SCAN`: inspect project structure, Python files, tests, and known
  configuration files.
- `RUN_TESTS`: run the configured pytest command with timeout and captured
  output.
- `READ_FILE`: read a permitted file inside the project.
- `APPLY_PATCH`: apply a patch to permitted Python source files.
- `REQUEST_APPROVAL`: ask the user to approve a guarded action.
- `FINISH`: stop with a structured result.

Initial tools:

- Project scanner.
- Fixed pytest runner.
- Safe file reader.
- Source patch applier.
- Approval request creator.
- Run log writer.

### 5.2 Objective Feedback Signal

The objective feedback signal is pytest output plus process metadata:

- exit code;
- stdout and stderr;
- timeout status;
- collected tests if available;
- failed test names;
- traceback excerpts;
- failure type.

The Feedback Engine converts raw pytest output into a `FailureSummary` with one
of these categories:

- `assertion_failure`: a test assertion failed.
- `runtime_exception`: code raised an unexpected exception.
- `import_error`: module or dependency import failed.
- `syntax_error`: Python syntax is invalid, often after a bad patch.
- `collection_error`: pytest could not collect tests.
- `timeout`: pytest exceeded the configured timeout.
- `unknown_failure`: the output did not match known patterns.

The next agent round receives a compact feedback object, not only a raw log. The
object includes the failed test, file paths, line hints, traceback summary, prior
patch summary, and a warning if the previous patch worsened the failure.

### 5.3 Dangerous Actions and Guardrails

Guardrails are deterministic code checks, not prompt instructions.

Path guardrails:

- All read and write paths are normalized and must remain inside the target
  project root.
- Reads of `.env`, private keys, certificates, credentials, token files, and
  common secret file patterns are rejected.
- Symlinks are resolved before path checks.

Write guardrails:

- Automatically allowed: ordinary `.py` source files outside test paths.
- Human approval required: test files, dependency files, configuration files,
  CI files, documentation, generated files, and lock files.
- Rejected by default: file deletion, binary writes, writes outside the project,
  and writes to sensitive files.

Command guardrails:

- Automatically allowed: the configured pytest command only.
- Human approval or rejection: dependency installation, network commands,
  publishing commands, arbitrary shell commands, and destructive commands.
- The LLM is not given a general-purpose shell tool in the first version.

### 5.4 Memory and Context

The first version uses small, explicit memory rather than a large autonomous
memory system.

Run-level memory:

- run id;
- project root;
- project scan summary;
- configured pytest command;
- each step's action, guardrail decision, tool result, feedback, and patch;
- final status and final diff.

Project-level lightweight memory:

- last successful test command;
- user-approved policy overrides;
- last known project layout summary;
- non-sensitive configuration metadata.

The context builder uses this memory to include only relevant information in the
next LLM call. It must not include API keys, `.env` contents, or full repository
content by default.

### 5.5 Stop Conditions

The agent stops when one of these conditions is true:

- pytest passes;
- the maximum repair round count is reached;
- a guardrail requires human approval;
- the LLM produces invalid structured output after retry;
- the same ineffective action repeats;
- pytest times out or the environment is unusable;
- the user cancels the run;
- the LLM emits `FINISH`.

### 5.6 Main Contribution

The main contribution is the pytest feedback loop:

1. run pytest;
2. parse raw output into structured feedback;
3. classify failure type;
4. summarize the relevant traceback and file hints;
5. feed the structured result back to the agent loop;
6. verify that the next action can change based on the feedback;
7. test the entire loop with a mock LLM.

This contribution is mechanism-heavy and testable without a real LLM. Guardrails
are the secondary contribution and support the required mechanism demo.

## 6. System Architecture

PyRepair Agent has two user entry points and one shared harness core.

```text
CLI / WebUI
   |
   v
Run Controller
   |
   v
Agent Core Loop
   |
   +--> LLM Client
   |      +--> MockLLMClient
   |      +--> OpenAICompatibleLLMClient
   |
   +--> Action Parser
   |
   +--> Guardrail Engine
   |
   +--> Tool Dispatcher
   |      +--> Project Scanner
   |      +--> Pytest Runner
   |      +--> Safe File Reader
   |      +--> Patch Applier
   |
   +--> Feedback Engine
   |
   +--> Memory / Run Store
```

### 6.1 Components

Run Controller:

- validates user input;
- creates a run id;
- starts, resumes, cancels, or inspects runs;
- exposes run state to CLI and WebUI.

Agent Core Loop:

- builds context;
- calls the injected LLM client;
- parses one action;
- asks guardrails for a decision;
- dispatches allowed tools;
- records results;
- feeds test feedback into the next round;
- enforces stop policy.

LLM Client:

- exposes a stable interface such as `generate(messages)`;
- supports mock scripts for tests;
- supports OpenAI-compatible chat completion for real runs.

Action Parser:

- validates model output against a strict action schema;
- rejects malformed JSON, unknown action names, missing fields, or unsafe
  payload shapes;
- returns parse errors as feedback rather than executing partial output.

Tool Dispatcher:

- maps validated actions to deterministic tool implementations;
- returns structured `ToolResult` records;
- never bypasses guardrails.

Guardrail Engine:

- evaluates actions before execution;
- returns allow, reject, or approval-required decisions;
- attaches a human-readable reason and machine-readable policy code.

Feedback Engine:

- parses pytest output;
- classifies failures;
- summarizes traces;
- produces compact feedback for the next loop.

Memory / Run Store:

- persists run steps as JSONL or SQLite records;
- supports WebUI inspection and deterministic test assertions.

CLI:

- provides commands for repair, demos, key management, and WebUI startup.

WebUI:

- displays run list, run detail, tool actions, feedback, diffs, guardrail events,
  and approval requests;
- uses the same backend as the CLI.

## 7. Functional Specification

### 7.1 CLI

Required commands:

- `pyrepair run <project-path>`: run repair on a local project.
- `pyrepair demo feedback-loop`: run deterministic mock feedback demo.
- `pyrepair demo guardrail`: run deterministic guardrail demo.
- `pyrepair demo full`: run all demos.
- `pyrepair key set`: securely enter API key.
- `pyrepair key status`: show whether a key is configured without revealing it.
- `pyrepair key clear`: remove stored API key.
- `pyrepair web`: start local WebUI.

Boundary behavior:

- Invalid project path returns a clear error.
- Missing pytest environment returns an environment failure summary.
- Missing real API key blocks real LLM mode but not mock demo mode.

### 7.2 WebUI

Required views:

- Runs: run id, project name, status, started time, final result.
- Run detail: step timeline with action, tool result, feedback category, and
  stop reason.
- Diff view: final patch and per-step patch.
- Guardrails: rejected and approval-required actions with reasons.
- Settings: LLM provider, base URL, model, key status, and safety policy summary.
- Demo: trigger mock-only demos against built-in fixture projects.

Public deployment mode:

- public WebUI must run in mock/demo-only mode;
- it must not accept arbitrary host paths;
- it must not expose real local files or shell execution.

### 7.3 Repair Run

Input:

- project path;
- optional config path;
- optional max rounds;
- optional LLM backend selection.

Behavior:

1. normalize and validate project path;
2. create run record;
3. scan project;
4. run pytest;
5. if tests pass, finish;
6. build context from failure summary and relevant run memory;
7. call LLM;
8. parse action;
9. evaluate guardrail;
10. execute allowed action;
11. record result;
12. repeat until stop condition.

Output:

- final status;
- final pytest summary;
- final diff;
- run log location;
- approval request if paused.

### 7.4 Human Approval

Approval is required for guarded actions such as modifying tests or dependency
files.

Approval request includes:

- action type;
- target files;
- reason for approval requirement;
- proposed diff when available;
- risk level;
- approve and reject choices.

Approval behavior:

- approve: execute the pending action and continue;
- reject: record the rejection and feed the reason back into the next agent
  step;
- cancel: stop the run.

### 7.5 Configuration

Configuration includes:

- LLM backend: mock or OpenAI-compatible;
- base URL;
- model;
- max rounds;
- pytest command;
- test timeout;
- allowed source path patterns;
- approval-required path patterns;
- output truncation limits.

Configuration must not include plaintext API keys.

## 8. Data Model

Model definitions must be explicit enough that a fresh implementation agent can
create `src/pyrepair/models.py` without guessing. The first implementation uses
Python enums and dataclasses. Serialization for run logs uses plain dicts with
enum values as strings.

### 8.1 Enums

`ActionType` string values:

- `PROJECT_SCAN`
- `RUN_TESTS`
- `READ_FILE`
- `APPLY_PATCH`
- `REQUEST_APPROVAL`
- `FINISH`

`RunStatus` string values:

- `RUNNING`
- `PASSED`
- `FAILED`
- `WAITING_APPROVAL`
- `CANCELLED`

`GuardrailDecisionType` string values:

- `ALLOW`
- `REJECT`
- `APPROVAL_REQUIRED`

`FailureCategory` string values:

- `NONE`
- `ASSERTION_FAILURE`
- `RUNTIME_EXCEPTION`
- `IMPORT_ERROR`
- `SYNTAX_ERROR`
- `COLLECTION_ERROR`
- `TIMEOUT`
- `UNKNOWN_FAILURE`

`TestStatus` string values:

- `PASSED`
- `FAILED`
- `ERROR`
- `TIMEOUT`

`ApprovalStatus` string values:

- `PENDING`
- `APPROVED`
- `REJECTED`
- `CANCELLED`

`LLMProvider` string values:

- `MOCK`
- `OPENAI_COMPATIBLE`

`ActionParseStatus` string values:

- `PARSED`
- `INVALID_JSON`
- `UNKNOWN_ACTION`
- `MISSING_FIELD`
- `INVALID_PAYLOAD`

### 8.2 Dataclasses

`Action`:

- `type: ActionType`, required.
- `payload: dict[str, object] = field(default_factory=dict)`.
- `raw_model_output: str = ""`.
- `parse_status: ActionParseStatus = ActionParseStatus.PARSED`.

`GuardrailDecision`:

- `decision: GuardrailDecisionType`, required.
- `policy_code: str = ""`.
- `reason: str = ""`.
- `risk_level: str = "low"`.

`FailureSummary`:

- `status: TestStatus = TestStatus.FAILED`.
- `category: FailureCategory = FailureCategory.UNKNOWN_FAILURE`.
- `failed_tests: list[str] = field(default_factory=list)`.
- `related_files: list[str] = field(default_factory=list)`.
- `traceback_excerpt: str = ""`.
- `line_hints: list[int] = field(default_factory=list)`.
- `message: str = ""`.

`TestResult`:

- `command: list[str] = field(default_factory=list)`.
- `exit_code: int = 0`.
- `duration_ms: int = 0`.
- `timed_out: bool = False`.
- `stdout: str = ""`.
- `stderr: str = ""`.
- `raw_output_ref: str = ""`.
- `failure_summary: FailureSummary | None = None`.

`ToolResult`:

- `tool_name: str`, required.
- `success: bool = False`.
- `stdout_summary: str = ""`.
- `stderr_summary: str = ""`.
- `exit_code: int | None = None`.
- `changed_files: list[str] = field(default_factory=list)`.
- `error: str = ""`.
- `test_result: TestResult | None = None`.
- `patch_record: PatchRecord | None = None`.

`PatchRecord`:

- `files_changed: list[str] = field(default_factory=list)`.
- `diff: str = ""`.
- `applied: bool = False`.
- `requires_approval: bool = False`.
- `source_step: int | None = None`.

`RunStep`:

- `run_id: str`, required.
- `round_index: int`, required.
- `llm_backend: str = ""`.
- `context_summary: str = ""`.
- `action: Action | None = None`.
- `guardrail_decision: GuardrailDecision | None = None`.
- `tool_result: ToolResult | None = None`.
- `feedback: FailureSummary | None = None`.
- `created_at: str = ""`.

`RunRecord`:

- `id: str`, required.
- `project_root: str`, required.
- `status: RunStatus = RunStatus.RUNNING`.
- `created_at: str = ""`.
- `updated_at: str = ""`.
- `max_rounds: int = 3`.
- `current_round: int = 0`.
- `steps: list[RunStep] = field(default_factory=list)`.
- `final_summary: str = ""`.

`ApprovalRequest`:

- `id: str`, required.
- `run_id: str`, required.
- `step_id: str = ""`.
- `action: Action | None = None`.
- `reason: str = ""`.
- `diff: str = ""`.
- `status: ApprovalStatus = ApprovalStatus.PENDING`.
- `decision_note: str = ""`.

`LLMConfig`:

- `provider: LLMProvider = LLMProvider.MOCK`.
- `base_url: str = ""`.
- `model: str = ""`.
- `api_key_ref: str = ""`.
- `timeout_seconds: int = 60`.
- `max_output_tokens: int = 2048`.

### 8.3 Serialization Rules

- Enums serialize to their string values.
- Nested dataclasses serialize recursively as dicts.
- `None` values may be emitted as JSON null.
- API keys and plaintext secrets must never be serialized.
- Run log records must be JSON-compatible.

## 9. Security and Credential Design

### 9.1 Credential Storage

The OpenAI-compatible backend requires an API key. The key must never be stored
in source code, committed to Git, printed in logs, displayed in WebUI, or written
to plain config files.

Preferred storage:

- system keyring through a Python keyring library.

Fallback storage:

- encrypted local file protected by a master password, if system keyring is not
  available on the target platform.

Environment variables may be supported as a secondary source, but README must
explain that process environments and `.env` files are plaintext risks.

### 9.2 Key Management UX

`pyrepair key set`:

- prompts with hidden input;
- stores the key securely;
- validates only format/presence locally unless user requests a real API smoke
  test.

`pyrepair key status`:

- reports configured or missing;
- reports provider, base URL, and model;
- never prints the key.

`pyrepair key clear`:

- removes the stored key.

### 9.3 Threat Model and Mitigations

API key leakage:

- secure storage;
- log redaction;
- no plaintext display;
- no key in config.

Sensitive file exposure:

- reject `.env`, private keys, certificates, credentials, and token-like files;
- do not include sensitive files in context.

Path traversal:

- normalize and resolve paths;
- enforce project-root containment;
- test symlink edge cases.

Untrusted LLM output:

- strict action schema;
- guardrail decision before tool dispatch;
- no arbitrary shell tool.

Test tampering:

- automatic writes to test files are blocked for human approval.

Cost or infinite loops:

- max rounds;
- LLM timeout;
- output limit;
- repeated-action stop condition.

Unsafe public WebUI:

- public deployment runs in mock/demo-only mode;
- local repair mode binds to localhost by default.

## 10. Non-Functional Requirements

### 10.1 Performance

- A default repair run should finish or pause within the configured maximum
  repair rounds.
- The default maximum is 3 repair rounds for demos and 5 repair rounds for real
  local use.
- Each pytest invocation has a configurable timeout. The default timeout is 60
  seconds for fixture demos and 300 seconds for real local projects.
- Captured stdout and stderr are persisted, but only bounded summaries are sent
  to the LLM and displayed by default.
- The WebUI should load a single run detail view from local run records without
  requiring another LLM call.

### 10.2 Availability and Reliability

- Mock demos must run offline without network access or API keys.
- Real LLM mode may fail because of provider, network, quota, or credential
  errors; these failures must stop the run with a clear status instead of
  crashing or retrying indefinitely.
- Tool execution failures are recorded as structured tool results and fed into
  the run state.
- The run log is append-only so that partial runs remain inspectable after an
  error.
- The public WebUI must remain usable in mock/demo-only mode even when no real
  key is configured.

### 10.3 Observability

- Each run has a stable run id.
- Each step records action, guardrail decision, tool result, feedback category,
  and stop reason when applicable.
- CLI output includes a compact step timeline and final status.
- WebUI exposes the same run timeline, pytest summary, patch diff, and guardrail
  events.
- Logs must redact secrets and avoid printing full API keys.

### 10.4 Usability

- CLI commands must return actionable errors for missing project paths, missing
  pytest, missing API keys, invalid model output, and approval-required actions.
- WebUI should be usable as an operational console, not a marketing page.
- Public demo mode should let reviewers inspect the harness mechanisms without
  setup.

## 11. Technical Choices

Language:

- Python, because the target domain is Python + pytest and it keeps the harness,
  tests, fixture projects, and packaging in one ecosystem.

Testing:

- pytest for unit, integration, and mock-loop tests.

CLI:

- Typer, because it provides typed commands with low overhead.

Web backend:

- FastAPI, because it can serve run APIs and simple HTML/JS views.

WebUI style:

- a restrained operational dashboard focused on dense run inspection.
- selected design approach: an Open Design-aligned operational console for
  run timelines, failure summaries, diffs, and guardrail decisions.
- before implementing the WebUI, the implementation plan must include a task to
  consult the Open Design guidance available in the development environment and
  record any deviation in `AGENT_LOG.md`.
- no new heavyweight frontend framework is required for the first version.

LLM:

- OpenAI-compatible chat completion API for real runs.
- Mock LLM for deterministic tests and demos.

Persistence:

- JSONL run logs for simple append-only evidence;
- SQLite may be added if WebUI querying becomes cumbersome.

Distribution:

- Python package for local CLI use;
- Docker image for reproducible execution.

Deployment platform:

- Primary public demo target: a Docker-compatible Render web service running
  mock/demo-only mode.
- The Docker image should remain portable to other OCI-compatible hosts if the
  final course environment prefers another platform.
- Real local repair is not exposed on the public deployment.

CI:

- GitHub Actions for public repository push tests;
- `.gitlab-ci.yml` with `unit-test` job to satisfy the course final checklist.

## 12. Testing and Mechanism Demonstration

### 12.1 Unit Tests

Required unit test groups:

- action parser tests;
- guardrail path policy tests;
- guardrail sensitive file tests;
- guardrail write policy tests;
- pytest output parser tests;
- failure classifier tests;
- stop policy tests;
- run store tests;
- credential status/redaction tests.

### 12.2 Mock LLM Loop Tests

Mock-loop tests must not access network or real APIs.

Required cases:

- mock LLM reads source, applies a bad patch, receives failure feedback, applies
  a corrected patch, and stops after pytest passes;
- mock LLM attempts to modify a test file, and the run pauses with
  approval-required status;
- mock LLM outputs malformed action JSON, and the parser rejects it without
  executing tools.

### 12.3 Fixture Projects

Required fixture:

```text
examples/buggy_calculator/
  src/calculator.py
  tests/test_calculator.py
```

The fixture starts with failing pytest tests. The mock feedback-loop demo repairs
it deterministically.

Additional fixtures may cover:

- import error;
- syntax error after bad patch;
- runtime exception.

### 12.4 Demo Commands

Required demo commands:

- `pyrepair demo feedback-loop`
- `pyrepair demo guardrail`
- `pyrepair demo full`

Each demo must print or expose:

- run id;
- step timeline;
- feedback category;
- guardrail decision when applicable;
- final status;
- final diff or approval request.

### 12.5 Real API Smoke Test

A manual smoke test may verify that the OpenAI-compatible backend can perform one
completion with configured credentials. It is not required in default CI because
CI must not require paid API keys.

## 13. Acceptance Criteria

Core harness:

- The agent main loop is implemented in this project.
- LLM backend is injectable.
- Mock LLM tests run offline and deterministically.
- No high-level agent framework provides the loop.

Feedback:

- pytest output is parsed into structured feedback.
- at least assertion failure, runtime exception, import error, syntax error, and
  timeout are classified or explicitly handled.
- feedback is included in the next loop context.
- mock loop proves feedback can change the next action.

Guardrails:

- project-root path containment is enforced.
- sensitive file reads are rejected.
- test-file writes require approval.
- source-file writes are allowed only under configured source policy.
- dangerous or arbitrary shell actions are not executed.

User interfaces:

- CLI can start a repair run and demos.
- WebUI can display run list, run detail, feedback, diff, and guardrail events.
- public WebUI mode is mock/demo-only.

Credentials:

- key set/status/clear commands exist.
- key status never prints plaintext key.
- README documents secure key setup and `.env` risks.

CI and distribution:

- one command runs the full offline test suite.
- GitHub Actions runs tests on push.
- `.gitlab-ci.yml` contains a `unit-test` job.
- Dockerfile or package instructions allow a fresh machine to run the project.

Process evidence:

- `SPEC.md`, `PLAN.md`, `SPEC_PROCESS.md`, `AGENT_LOG.md`, and `REFLECTION.md`
  are present by final submission.
- PLAN tasks are updated with completion status and commit hashes.
- each major module is developed in a worktree-backed branch and reviewed through
  PR/MR evidence.

## 14. CI, Distribution, and Deployment

### 14.1 CI

Both CI definitions should call the same offline test command.

Canonical offline test command:

- `make test`

`make test` should run unit tests and mock integration tests only. It must not
require network access or real API keys.

GitHub Actions:

- runs unit and mock integration tests on push and PR;
- optionally builds the Docker image.

GitLab CI:

- `.gitlab-ci.yml` includes a job named `unit-test`;
- `unit-test` runs the same offline test command;
- final submitted pipeline should be passing.

### 14.2 Distribution

Python package distribution:

- README documents installation and CLI usage.
- package metadata lists dependencies and supported Python versions.

Docker distribution:

- Dockerfile builds the project;
- README documents build and run commands;
- README explains how to mount a target project into the container;
- README explains how credentials are configured safely.

### 14.3 Deployment URL

The deployed WebUI for final submission runs in mock/demo-only mode. It provides
an accessible public URL for reviewers to inspect the UI and mechanism demos
without exposing local files, credentials, or shell execution.

Real project repair remains a local workflow.

## 15. Superpowers Workflow and Process Evidence

The project must follow the required Superpowers workflow:

1. brainstorming;
2. writing-plans;
3. using-git-worktrees;
4. subagent-driven-development or executing-plans;
5. test-driven-development;
6. requesting-code-review;
7. finishing-a-development-branch.

Deviations are allowed only with a reason recorded in `AGENT_LOG.md`.

### 15.1 SPEC_PROCESS.md

`SPEC_PROCESS.md` must record:

- key brainstorming questions;
- at least three important design iterations;
- AI suggestions accepted by the human owner;
- AI suggestions rejected or revised, with reasons;
- cold-start validation results from a different agent;
- SPEC/PLAN revisions made after cold-start feedback.

### 15.2 PLAN.md

`PLAN.md` must be produced after SPEC approval. Each task must include:

- task id;
- goal;
- files affected;
- expected implementation points;
- TDD red test to write first;
- verification command;
- dependencies;
- whether it can be parallelized;
- completion status;
- commit hash after completion.

Tasks should be small enough for a subagent to complete in one focused session.

### 15.3 Worktree and PR/MR Evidence

The repository should use separate branches or worktrees for major modules, for
example:

- `feature/core-loop`
- `feature/feedback-engine`
- `feature/guardrails`
- `feature/cli-webui`
- `feature/distribution-ci`

Each feature branch should have a PR/MR or equivalent review record. Each PR/MR
description should include:

- related PLAN task ids;
- subagent used;
- TDD red/green/refactor summary;
- manual changes by the human owner;
- verification commands and results;
- risks or follow-up notes.

### 15.4 AGENT_LOG.md

`AGENT_LOG.md` must be maintained chronologically. Each entry should include:

- timestamp;
- task id;
- Superpowers skill invoked;
- important prompt/context choices;
- subagent summary;
- commit hash or PR/MR link;
- human intervention;
- lesson learned.

### 15.5 Review Discipline

Each task must go through:

1. spec compliance review;
2. code quality review;
3. fix of critical issues before the next task starts.

Completion claims must be backed by actual verification output.

## 16. Final Deliverables Checklist

Final submission must include:

- `SPEC.md`.
- `PLAN.md`.
- `SPEC_PROCESS.md`, including at least three key brainstorming dialogue
  excerpts, the human handling decision for each excerpt, and cold-start
  validation results from a different agent.
- Complete source code for the self-implemented harness core.
- Mock-LLM unit tests and mock integration tests for the core mechanisms.
- Mechanism demos for guardrail interception, failure injection with feedback
  loop correction, and the main feedback-loop contribution.
- `README.md` with project introduction, installation, running commands,
  distribution commands, directory structure, key setup, known limits, and safety
  boundaries.
- `AGENT_LOG.md`, maintained throughout implementation.
- `REFLECTION.md`, 1500-2500 Chinese characters, written by the student; AI may
  only be used for polishing if that assistance is disclosed.
- GitHub Actions configuration and last successful run evidence.
- `.gitlab-ci.yml` with a `unit-test` job and last successful CI/CD evidence on
  the required submission platform if available.
- Dockerfile and/or Python package metadata plus instructions for fresh-machine
  setup.
- Public WebUI URL running mock/demo-only mode.
- PR/MR or equivalent review evidence for major worktree-backed feature
  branches.
- Commit history showing incremental work rather than a single final commit.
- No real API keys, tokens, credentials, `.env` contents, or private secrets in
  source, history, logs, or submitted artifacts.

Repository hosting requirement:

- The final repository should be public when allowed by the course platform.
- If it must remain private, teaching staff must be added according to course
  instructions.
- Implementation should start in the final repository so branch, worktree,
  commit, PR/MR, and CI evidence are collected naturally.

## 17. Risks and Mitigations

Pytest output variation:

- keep parser conservative;
- store raw output reference;
- classify unknown patterns as `unknown_failure`.

Real LLM unpredictability:

- core grading demos use mock LLM;
- real LLM mode is treated as best-effort.

Overbroad scope:

- first version is Python + pytest only;
- no arbitrary shell tool;
- no multi-language repair.

Test tampering:

- automatic test modification is blocked by guardrails.

Credential handling differences across platforms:

- prefer system keyring;
- provide documented fallback;
- do not require real keys in CI.

Public WebUI risk:

- public deployment is mock/demo-only;
- real repair is local-only.

CI requirement ambiguity:

- provide both GitHub Actions and `.gitlab-ci.yml`;
- ensure `.gitlab-ci.yml` contains `unit-test`.

Missing process evidence:

- record PR/worktree/subagent decisions during implementation, not after the
  fact;
- update `PLAN.md` and `AGENT_LOG.md` after every task.

Current repository setup risk:

- implementation should not begin until the project is initialized as a Git
  repository or moved into the final course repository, so commit, branch,
  worktree, and PR/MR evidence can be collected from the start.
