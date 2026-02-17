from __future__ import annotations

from .bullets_mixin import BulletsToolsMixin
from .core_mixin import CoreToolsMixin
from .finalize_mixin import FinalizeToolsMixin
from .parsing_mixin import ParsingToolsMixin
from .summary_mixin import SummaryToolsMixin


class ResumeAgentTools(
    FinalizeToolsMixin,
    BulletsToolsMixin,
    SummaryToolsMixin,
    ParsingToolsMixin,
    CoreToolsMixin,
):
    """Composed toolset split by domain modules."""


__all__ = ["ResumeAgentTools"]
