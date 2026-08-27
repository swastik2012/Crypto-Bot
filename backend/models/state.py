from typing import TypedDict, List, Dict, Any, Optional
from backend.models.schemas import (
    Stage1GeminiVisionResult,
    Stage2NewsSentimentResult,
    Stage3NvidiaNimResult,
    Stage4OpenAIRiskResult,
    Stage5GeminiArbiterResult,
    DebateMessageSchema,
    PaperAccountState,
)

class AgentGraphState(TypedDict):
    # Input Context
    symbol: str
    timeframe: str
    chart_image_base64: Optional[str]
    current_price: float
    strategy_preset: str
    account_state: Dict[str, Any]
    
    # API Keys Configuration
    gemini_key: Optional[str]
    nvidia_key: Optional[str]
    openai_key: Optional[str]
    
    # 5-Stage Outputs
    stage1_output: Optional[Stage1GeminiVisionResult]
    stage2_output: Optional[Stage2NewsSentimentResult]
    stage3_output: Optional[Stage3NvidiaNimResult]
    stage4_output: Optional[Stage4OpenAIRiskResult]
    stage5_output: Optional[Stage5GeminiArbiterResult]
    
    # Inter-Agent Dialogue Stream
    debate_messages: List[DebateMessageSchema]
    
    # Execution Flags
    auto_execute_approved: bool
    final_error: Optional[str]
