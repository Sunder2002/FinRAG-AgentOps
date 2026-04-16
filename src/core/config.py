import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

class Settings(BaseSettings):
    PROJECT_NAME: str = "FinRAG-AgentOps"
    GOOGLE_API_KEY: str
    SEC_USER_AGENT: str = "EnterpriseAuditSystem/1.0 (audit@firm.com)"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

# --- ENTERPRISE OBSERVABILITY & LOGGING ---
# Remove default logger
logger.remove()

# 1. Console Output (For your terminal, with colors)
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>")

# 2. Persistent File Logging (For error analysis and monitoring)
# This creates an app.log file. If it hits 10MB, it archives it and creates a new one.
logger.add("app.log", rotation="10 MB", retention="10 days", level="INFO", backtrace=True, diagnose=True)

logger.info(f"🚀 Initialized System Configuration & Observability for {settings.PROJECT_NAME}")