"""Application-level entry point for repair runs."""

from __future__ import annotations

from pathlib import Path

from pyrepair.config import RepairConfig
from pyrepair.core import AgentCoreLoop
from pyrepair.llm import LLMClient, MockLLMClient
from pyrepair.models import LLMProvider, RunRecord


class RunController:
    """Start repair runs with an injectable core loop or LLM client."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        core_loop: AgentCoreLoop | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._core_loop = core_loop

    def start_run(self, project_root: Path, config: RepairConfig) -> RunRecord:
        """Validate the target directory and delegate the bounded run to the core loop."""
        root = project_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"project path is not a directory: {project_root}")
        if self._core_loop is not None:
            return self._core_loop.run(root, config)
        if (
            config.llm_provider is LLMProvider.OPENAI_COMPATIBLE
            and self._llm_client is None
        ):
            raise ValueError("OpenAI-compatible provider requires an injected LLM client.")
        return AgentCoreLoop(self._llm_client or MockLLMClient([])).run(root, config)
