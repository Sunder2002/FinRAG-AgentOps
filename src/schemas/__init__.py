from pydantic import BaseModel, Field

class AuditRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g., MSFT, AAPL)")

class TaskResponse(BaseModel):
    task_id: str
    status: str