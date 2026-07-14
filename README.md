# PyRepair Agent

PyRepair Agent is a Python and pytest coding-agent harness for small local
projects. It turns pytest output into structured feedback, asks an injected LLM
backend for one structured next action, and applies deterministic guardrails
before tools can read or modify project files. The bundled mock backend keeps
tests and demonstrations offline and repeatable.

## Installation

Use Python 3.11 or newer. Create and activate a virtual environment, then
install the package with test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

## Running CLI

Run the guarded repair flow for a local pytest project:

```powershell
pyrepair run path\\to\\project
```

The default CLI configuration uses the offline mock backend. Review the final
status and run records before keeping any generated patch.

## Running WebUI

Start the local, demo-only console:

```powershell
pyrepair web
```

Open `http://127.0.0.1:8000` in a browser. This console exposes only bundled
mock demonstrations; it does not accept arbitrary host paths or provide a
general shell.

## Public WebUI

The public mock/demo-only WebUI is available at:

https://pyrepair-agent-demo.glossy-otter-9952.chatgpt.site

This deployment is an online demonstration console. It exposes deterministic
mock run data for the feedback-loop and guardrail mechanisms, and it does not
connect to local files, shell execution, provider credentials, or a real LLM.

## Demo Commands

The demos run from temporary copies of the bundled calculator fixture and do
not require a network connection or provider credentials:

```powershell
pyrepair demo feedback-loop
pyrepair demo guardrail
pyrepair demo full
```

## Distribution Commands

Build a source distribution and wheel with the standard Python build frontend:

```powershell
python -m pip install build
python -m build
```

The generated artifacts are written to `dist/`. Do not publish an artifact
until the local tests and the release process have been reviewed.

## Docker Build and Run

Build the image and run the offline mock demo that is configured as its default
command:

```powershell
docker build -t pyrepair-agent .
docker run --rm pyrepair-agent
```

To expose the local demo-only WebUI from a container, override the command and
bind a deliberate local port:

```powershell
docker run --rm -p 8000:8000 pyrepair-agent pyrepair web --host 0.0.0.0 --port 8000
```

## Directory Structure

```text
src/pyrepair/       Package source: CLI, core loop, guardrails, tools, WebUI
tests/              Offline pytest unit tests
examples/           Bundled deterministic fixture projects
.github/workflows/  GitHub Actions workflow
.gitlab-ci.yml      GitLab CI configuration
Dockerfile          Offline demo image definition
SPEC.md             Product and mechanism specification
PLAN.md             Task-by-task implementation plan
```

## Secure Key Configuration

For an OpenAI-compatible provider, use the key-management commands. The CLI
uses the system credential store when it is available and never prints the
stored value:

```powershell
pyrepair key set --provider openai
pyrepair key status --provider openai
pyrepair key clear --provider openai
```

Use mock demos when no system credential backend is available. Do not place a
provider key in source code, commits, issue text, run logs, or screenshots.

## `.env` Risk Warning

Environment variables and `.env` files are plaintext configuration surfaces:
they can leak through process inspection, shell history, editor tooling, crash
reports, backups, or accidental commits. `.env` patterns are ignored by this
repository, but ignored files are not secure storage. Prefer the system
credential store and rotate a credential if it is exposed.

## Safety Boundaries

- The LLM proposes structured actions; it does not receive a general-purpose shell.
- The fixed pytest command is the only automatically allowed command.
- Automatic writes are limited to ordinary Python source files inside the target project.
- Tests, dependency files, configuration, CI, documentation, generated files, and lock files require approval.
- Sensitive files, binary writes, deletions, and paths outside the target project are rejected.
- The public-facing WebUI mode is mock/demo-only and does not expose host file access.

## Known Limitations

- The first version targets small Python projects that use pytest only.
- Repair quality depends on the configured model and the available failure context.
- The harness does not install dependencies, edit lock files, or make arbitrary shell calls automatically.
- Mock demos prove the feedback and guardrail mechanisms; they are not evidence that a real provider will repair every project.
- The credential backend relies on platform support and may be unavailable in constrained environments.

## CI Commands

The canonical offline test command is:

```powershell
make test
```

GitHub Actions and GitLab CI install the package with development dependencies
and run this command. On Windows hosts without `make`, use the equivalent local
command below and record that `make test` was unavailable:

```powershell
python -m pytest -q
```

This repository does not claim a remote CI result until the selected platform
has executed the workflow.
