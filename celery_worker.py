import os
import asyncio
from celery import Celery
from src.core.config import logger
from src.agents.audit_graph import audit_app
from src.services.sec_service import sec_service
from src.services.vector_service import vector_manager
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize Celery with Redis as the message broker
celery_app = Celery(
    "audit_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Celery is synchronous by default, but our SEC service is async.
# We wrap the async logic so Celery can run it properly.
@celery_app.task(bind=True, name="run_financial_audit")
def run_financial_audit_task(self, ticker: str):
    logger.info(f"👷 [Worker] Grabbed task for {ticker}. Executing...")
    
    # Create an event loop for the async execution
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_async_audit_logic(ticker))

async def _async_audit_logic(ticker: str):
    try:
        # 1. Fetch SEC Data
        docs = await sec_service.fetch_documents(ticker)
        if not docs:
            return {"status": "failed", "error": "No SEC documents found."}
        
        # 2. Chunk & Embed (Instant because model is already in memory!)
        chunks = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20).split_text(docs[0]["content"])
        vector_manager.upsert_documents(chunks, [{"ticker": ticker} for _ in chunks])
        
        # 3. RAG Search
        context = vector_manager.search("revenue growth")
        
        # 4. Multi-Agent Graph Execution
        initial_state = {"ticker": ticker, "db_context": context, "analyst_summary": "", "final_report": ""}
        result = audit_app.invoke(initial_state)
        
        logger.info(f"✅ [Worker] Finished audit for {ticker}")
        return {"status": "success", "report": result["final_report"]}
        
    except Exception as e:
        logger.error(f"❌ [Worker] Audit failed for {ticker}: {str(e)}")
        return {"status": "failed", "error": str(e)}