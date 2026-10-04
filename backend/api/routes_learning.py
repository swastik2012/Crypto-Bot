from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from backend.services.learning_memory import learning_memory_service
from backend.models.schemas import AIPlaybookSummary

router = APIRouter(prefix="/api/learning", tags=["Continuous AI Trade Learning & Playbook"])

@router.get("/summary", response_model=AIPlaybookSummary)
async def get_learning_summary():
    """
    Returns an overview of the AI's continuous trade learning engine:
    total trades audited, win/loss rules, evolving playbook, and cloud AI agent scorecards.
    """
    return learning_memory_service.get_playbook_summary()

@router.get("/playbook")
async def get_trading_playbook():
    """
    Returns the active set of evolving trading rules synthesized by the AI Trade Learner.
    """
    return {
        "status": "success",
        "count": len(learning_memory_service.playbook_rules),
        "rules": [r.dict() for r in learning_memory_service.playbook_rules],
    }

@router.get("/post-mortems")
async def get_trade_post_mortems(limit: int = Query(50, ge=1, le=150)):
    """
    Returns the rich chronological list of all AI post-mortems for winning and losing trades.
    """
    recent = learning_memory_service.learnings[::-1][:limit]
    return {
        "status": "success",
        "total_records": len(learning_memory_service.learnings),
        "post_mortems": [p.dict() for p in recent],
    }

@router.post("/audit-all")
async def audit_all_historical_trades(limit: int = Query(15, ge=1, le=50)):
    """
    Triggers the AI Trade Learning Model to audit historical closed trades
    and extract newly discovered rules for the playbook.
    """
    result = await learning_memory_service.audit_all_historical_trades(limit=limit)
    return result

@router.get("/scorecards")
async def get_agent_scorecards():
    """
    Returns accuracy and reliability scorecards for each cloud AI agent (Gemini Vision, DeepSeek, OpenAI Risk, Gemini Arbiter).
    """
    return {
        "status": "success",
        "scorecards": learning_memory_service.agent_scorecards,
    }
