"""Public configuration for bounded repair runs."""

from dataclasses import dataclass

from pyrepair.core import RepairConfig as CoreRepairConfig
from pyrepair.models import LLMProvider


@dataclass
class RepairConfig(CoreRepairConfig):
    """Core run settings plus the configured LLM provider selection."""

    llm_provider: LLMProvider = LLMProvider.MOCK


__all__ = ["RepairConfig"]
