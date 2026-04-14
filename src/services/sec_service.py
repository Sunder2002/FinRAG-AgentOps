import httpx
from src.core.config import settings, logger
from src.services.base import BaseAuditDataSource

class SECService(BaseAuditDataSource):
    def __init__(self):
        self.headers = {"User-Agent": settings.SEC_USER_AGENT}

    async def fetch_documents(self, ticker: str, limit: int = 1) -> list:
        logger.info(f"Mocking SEC fetch for {ticker}...")
        mock_text = f"ITEM 1. BUSINESS. {ticker} Inc. is a leading tech company. Revenue grew 15%."
        return [{"content": mock_text, "metadata": {"ticker": ticker}}]

sec_service = SECService()