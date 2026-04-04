from typing import List, Union
import secrets
import logging
from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Project Paths
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Database
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'health_ai_v2.db')}"),
    )
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # LLM
    OPENAI_API_KEY: Union[str, None] = os.getenv("OPENAI_API_KEY", None)
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "kimi-k2.5")

    # Baidu OCR (Task 43)
    BAIDU_APP_ID: str = os.getenv("BAIDU_APP_ID", "")
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY: str = os.getenv("BAIDU_SECRET_KEY", "")
    
    # Upload Directory (Task 56)
    UPLOAD_DIR: str = os.path.join(PROJECT_ROOT, "uploads")

    # Vision Model (EfficientNet multi-task nutrition regression)
    NUTRITION_MODEL_PATH: str = os.getenv(
        "NUTRITION_MODEL_PATH",
        os.path.join(os.path.dirname(PROJECT_ROOT), "models", "nutrition_efficientnet.pth")
    )
    
    # Redis Cache (Task 108)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

settings = Settings()
logger = logging.getLogger(__name__)

if os.getenv("HEALTHAI_DEBUG_CONFIG") == "1":
    logger.debug("=" * 60)
    masked_key = f"{settings.OPENAI_API_KEY[:5]}***" if settings.OPENAI_API_KEY else "NONE"
    logger.debug("CONFIG DEBUG: Loaded OpenAI API Key: %s", masked_key)
    logger.debug("CONFIG DEBUG: Base URL: %s", settings.OPENAI_BASE_URL)
    logger.debug("CONFIG DEBUG: Model: %s", settings.OPENAI_MODEL)
    logger.debug("=" * 60)
