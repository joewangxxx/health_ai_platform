from typing import List, Union
import json
import secrets
import logging
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from backend.config import BACKEND_DIR, MODELS_DIR

DEFAULT_BACKEND_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    # 60 分钟 * 24 小时 * 8 天 = 8 天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # 项目路径
    PROJECT_ROOT: str = BACKEND_DIR
    
    # 数据库
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'health_ai_v2.db')}"),
    )
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = DEFAULT_BACKEND_CORS_ORIGINS.copy()
    
    # 大语言模型配置
    OPENAI_API_KEY: Union[str, None] = os.getenv("OPENAI_API_KEY", None)
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "kimi-k2.5")

    # 百度 OCR（任务 43）
    BAIDU_APP_ID: str = os.getenv("BAIDU_APP_ID", "")
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY: str = os.getenv("BAIDU_SECRET_KEY", "")
    BAIDU_OCR_CONNECTION_TIMEOUT_MS: int = int(os.getenv("BAIDU_OCR_CONNECTION_TIMEOUT_MS", "5000"))
    BAIDU_OCR_SOCKET_TIMEOUT_MS: int = int(os.getenv("BAIDU_OCR_SOCKET_TIMEOUT_MS", "15000"))
    OCR_PROCESSING_TIMEOUT_SECONDS: float = float(os.getenv("OCR_PROCESSING_TIMEOUT_SECONDS", "60"))
    
    # 上传目录（任务 56）
    UPLOAD_DIR: str = os.path.join(PROJECT_ROOT, "uploads")

    # 视觉模型（EfficientNet 多任务营养回归）
    NUTRITION_MODEL_PATH: str = os.getenv(
        "NUTRITION_MODEL_PATH",
        os.path.join(MODELS_DIR, "nutrition_efficientnet.pth")
    )
    
    # Redis 缓存（任务 108）
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if v is None:
            return DEFAULT_BACKEND_CORS_ORIGINS.copy()

        raw_origins: List[str]
        if isinstance(v, str):
            value = v.strip()
            if not value:
                raw_origins = []
            elif value.startswith("["):
                loaded = json.loads(value)
                if not isinstance(loaded, list):
                    raise ValueError("BACKEND_CORS_ORIGINS must be a list")
                raw_origins = [str(origin).strip() for origin in loaded]
            else:
                raw_origins = [origin.strip() for origin in value.split(",")]
        elif isinstance(v, list):
            raw_origins = [str(origin).strip() for origin in v]
        else:
            raise ValueError(v)

        origins = [origin for origin in raw_origins if origin and origin != "*"]
        return origins or DEFAULT_BACKEND_CORS_ORIGINS.copy()

settings = Settings()
logger = logging.getLogger(__name__)

if os.getenv("HEALTHAI_DEBUG_CONFIG") == "1":
    logger.debug("=" * 60)
    masked_key = f"{settings.OPENAI_API_KEY[:5]}***" if settings.OPENAI_API_KEY else "NONE"
    logger.debug("CONFIG DEBUG: Loaded OpenAI API Key: %s", masked_key)
    logger.debug("CONFIG DEBUG: Base URL: %s", settings.OPENAI_BASE_URL)
    logger.debug("CONFIG DEBUG: Model: %s", settings.OPENAI_MODEL)
    logger.debug("=" * 60)
