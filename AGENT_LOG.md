# PyRepair Agent AGENT_LOG

This log records process evidence for the AI4SE PyRepair Agent project.

| Timestamp | Task | Superpowers Skill | Context / Prompt | Subagent Output | Human Intervention | Commit / PR | Lesson |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-12 | Brainstorming | using-superpowers, brainstorming | Read `AI4SE_Final_Project_A_Coding_Agent_Harness.md` and `General_Requirements.md`; proposed three project directions. | N/A | Human selected Test-Repair Coding Agent. | N/A | A scoped pytest feedback loop is stronger than a broad general agent. |
| 2026-07-12 | SPEC | brainstorming | Iteratively confirmed Python + pytest, local project path input, CLI-first + WebUI console, OpenAI-compatible backend, source-only automatic writes. | N/A | Human clarified API key expectations and test-file modification policy. | N/A | Guardrails must be code mechanisms, not prompt reminders. |
| 2026-07-12 | SPEC | brainstorming | Wrote and self-reviewed `SPEC.md`; checked for incomplete markers and course requirement coverage. | N/A | Human reminded to preserve PR/worktree evidence. | N/A | Process evidence must be planned before implementation, not reconstructed later. |
| 2026-07-12 | PLAN | writing-plans | Wrote `PLAN.md` with TDD tasks, mock LLM tests, CI, distribution, cold-start validation, and PR/worktree evidence. | N/A | Human selected Subagent-Driven execution. | N/A | The plan must stop before implementation if Git evidence cannot be collected. |
| 2026-07-12 | Repository setup | using-git-worktrees | `git status --short` failed because `.git` was invalid; attempted `git init -b main`. | N/A | First attempt failed with permission denied; user-facing approval request was made and approved. | N/A | Permission and repository-state blockers must be surfaced instead of bypassed. |
| 2026-07-12 | Cold-start validation | subagent-driven-development | Spawned a worker agent with no conversation context; instructed it to read only `SPEC.md` and `PLAN.md` and attempt PLAN Task 3. | Agent reported Task 3 intent was understandable but model enums, fields, defaults, nested relationships, and allowed values were under-specified. It did not modify files. | Revised `SPEC.md` Data Model and `PLAN.md` Task 3 with exact enum/dataclass/serialization contract. | N/A | Cold-start validation caught a real spec gap before implementation. |
