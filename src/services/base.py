from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAuditDataSource(ABC):
    @abstractmethod
    async def fetch_documents(self, ticker: str, limit: int = 1) -> List[Dict[str, Any]]:
        pass