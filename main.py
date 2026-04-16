from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings, logger
from contextlib import asynccontextmanager
from celery.result import AsyncResult

# Import our schemas and the background task dispatcher
from src.schemas import AuditRequest, TaskResponse
from celery_worker import run_financial_audit_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Principal Engineer Tip: Initialization logic goes here 
    # (e.g., pre-loading ML models or checking DB connections)
    logger.info(f"--- Booting {settings.PROJECT_NAME} ---")
    yield
    logger.info(f"--- Shutting down {settings.PROJECT_NAME} ---")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Enterprise Security: Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to internal domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Service health check for load balancers."""
    return {
        "status": "operational",
        "version": "1.0.0",
        "services": {
            "api": "healthy",
            "redis_broker": "configured", 
            "vector_store": "local_faiss"
        }
    }

@app.get("/")
async def root():
    """Automatically redirect the base URL to the API Dashboard."""
    return RedirectResponse(url="/docs")

# --- ENTERPRISE AUDIT ENDPOINTS ---

@app.post("/api/v1/audit", response_model=TaskResponse)
async def trigger_audit(request: AuditRequest):
    """
    Submits a ticker for a multi-agent financial audit. 
    Returns a task ID instantly so the UI doesn't freeze.
    """
    try:
        # .delay() pushes the job to the Redis queue for the Celery Worker
        task = run_financial_audit_task.delay(request.ticker)
        logger.info(f"Dispatched Audit Task {task.id} for {request.ticker}")
        return TaskResponse(task_id=task.id, status="processing")
    except Exception as e:
        logger.error(f"Failed to dispatch task. Is Redis running? Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Message Broker Error.")

@app.get("/api/v1/audit/{task_id}")
async def get_audit_status(task_id: str):
    """
    Poll this endpoint with the task_id to get the final agent report.
    """
    task_result = AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

if __name__ == "__main__":
    import uvicorn
    # reload=True is for development only
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)