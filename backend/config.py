import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# Explicitly load .env from backend directory or project root
backend_env = Path(__file__).resolve().parent / ".env"
root_env = Path(__file__).resolve().parent.parent / ".env"

if backend_env.exists():
    load_dotenv(dotenv_path=backend_env, override=True)
elif root_env.exists():
    load_dotenv(dotenv_path=root_env, override=True)

class Settings(BaseSettings):
    APP_NAME: str = "AetherTrade AI Backend"
    APP_VERSION: str = "2.5.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # AI API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    NVIDIA_API_KEY: Optional[str] = os.getenv("NVIDIA_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY", os.getenv("NVIDIA_API_KEY", ""))

    # Aliases & Model Settings
    NVIDIA_NIM_API_KEY: Optional[str] = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    NVIDIA_ENDPOINT: str = os.getenv("NVIDIA_ENDPOINT", "https://integrate.api.nvidia.com/v1")
    NVIDIA_DEEPSEEK_MODEL: str = os.getenv("NVIDIA_DEEPSEEK_MODEL", "deepseek-ai/deepseek-r1")
    NVIDIA_KIMI_MODEL: str = os.getenv("NVIDIA_KIMI_MODEL", "moonshotai/kimi-k2.6")
    NVIDIA_REASONING_MODEL: str = os.getenv("NVIDIA_REASONING_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    NVIDIA_FLAGSHIP_MODEL: str = os.getenv("NVIDIA_FLAGSHIP_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Model Defaults
    DEFAULT_GEMINI_MODEL: str = "gemini-3.7-flash"
    DEFAULT_NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    DEFAULT_NVIDIA_ENDPOINT: str = "https://integrate.api.nvidia.com/v1"
    DEFAULT_OPENAI_MODEL: str = "gpt-4o"
    DEFAULT_DEEPSEEK_MODEL: str = "deepseek-ai/deepseek-r1"
    DEFAULT_KIMI_MODEL: str = "moonshotai/kimi-k2.6"
    
    # Paper Trading Defaults
    DEFAULT_STARTING_BALANCE: float = 10000.0
    DEFAULT_QUOTE_CURRENCY: str = "USDT"
    DEFAULT_RISK_PER_TRADE_PERCENT: float = 5.0
    DEFAULT_MAX_LEVERAGE: int = 20
    
    # Consensus Threshold for Auto-Execution
    AUTO_EXECUTE_CONFIDENCE_THRESHOLD: float = 80.0

    class Config:
        env_file = str(backend_env) if backend_env.exists() else None
        extra = "allow"

settings = Settings()
