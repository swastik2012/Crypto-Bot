"""
Legacy Stage Jev System One Adapter.
This module seamlessly forwards all calls to the upgraded NVIDIA DeepSeek Reasoning Agent (Stage 3).
"""

from backend.agents.stage3_nvidia_deepseek import run_stage3_nvidia_deepseek as run_stage_jev_system_one
from backend.models.schemas import StageDeepSeekReasoningResult as StageJevSystemOneResult, DeepSeekQuestionResult as JevQuestionResult

__all__ = ["run_stage_jev_system_one", "StageJevSystemOneResult", "JevQuestionResult"]
