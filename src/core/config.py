import logging
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FinRAG-AgentOps"
    
    # We only need these two keys now
    GOOGLE_API_KEY: str
    SEC_USER_AGENT: str = "EnterpriseAuditSystem/1.0 (audit@firm.com)"
    
    # extra="ignore" prevents crashes from old .env variables
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("FinRAG-Principal")

logger = setup_logging()