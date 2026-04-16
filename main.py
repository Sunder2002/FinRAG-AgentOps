import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings, logger
from contextlib import asynccontextmanager
from celery import Celery
from celery.result import AsyncResult
from pydantic import BaseModel

# 🛑 STRICT DECOUPLING: Define a pure Celery client. 
# DO NOT import celery_worker.py. No ML models are loaded in this container.
celery_app = Celery(
    "audit_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

class AuditRequest(BaseModel):
    ticker: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"--- Booting {settings.PROJECT_NAME} API Gateway ---")
    yield
    logger.info(f"--- Shutting down {settings.PROJECT_NAME} ---")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Enterprise Security: Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "operational",
        "version": "1.0.0",
        "services": {
            "api": "healthy",
            "redis_broker": "configured", 
            "vector_store": "qdrant_remote"
        }
    }

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.post("/api/v1/audit", response_model=TaskResponse)
async def trigger_audit(request: AuditRequest):
    try:
        # Send the task by its string name via Redis. API stays lightning fast.
        task = celery_app.send_task("run_financial_audit", args=[request.ticker])
        logger.info(f"Dispatched Audit Task {task.id} for {request.ticker}")
        return TaskResponse(task_id=task.id, status="processing")
    except Exception as e:
        logger.error(f"Failed to dispatch task. Is Redis running? Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Message Broker Error.")

@app.get("/api/v1/audit/{task_id}")
async def get_audit_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.result
        else:
            response["error"] = str(task_result.info)
            
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)