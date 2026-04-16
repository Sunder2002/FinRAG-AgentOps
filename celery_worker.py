import asyncio
import os
from celery import Celery
from src.core.config import logger
from src.services.sec_service import sec_service
from src.services.vector_service import vector_manager
from src.agents.audit_graph import audit_app

celery_app = Celery(
    "audit_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

@celery_app.task(name="run_financial_audit")
def run_financial_audit_task(ticker: str):
    logger.info(f"👨‍🍳 Chef received order for {ticker}")
    
    try:
        # 1. Fetch Live Data
        documents = asyncio.run(sec_service.fetch_documents(ticker))
        
        if not documents:
            return {"status": "failed", "report": f"No financial documents found for {ticker}."}

        # Combine all fetched text
        full_text = "\n".join([doc["content"] for doc in documents])
        
        # 2. ELITE FIX: Adaptive Context Routing (Agentic Best Practice)
        # If the payload is massive, use the Vector DB. 
        # If it is small, bypass the database entirely to prevent unnecessary failure points.
        if len(full_text) > 8000:
            logger.info("📚 Large document detected. Routing to Qdrant Vector DB...")
            texts = [doc["content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            success = vector_manager.upsert_documents(texts, metadatas)
            if success:
                db_context = vector_manager.search(f"Financial revenue and income data for {ticker}")
            else:
                logger.warning("⚠️ DB Ingestion failed. Injecting raw text directly into agent context.")
                db_context = full_text[:8000] 
        else:
            logger.info("⚡ Small document detected. Bypassing Vector DB for direct injection...")
            db_context = full_text

        # 3. Execute LangGraph Agents
        logger.info("🚀 Igniting LangGraph Agentic Loop...")
        initial_state = {"ticker": ticker, "db_context": db_context}
        final_state = audit_app.invoke(initial_state)
        
        # Ensure we always return the string report
        report_text = final_state.get("final_report", "Error: Agent failed to generate report.")
        return {"status": "success", "report": report_text}
        
    except Exception as e:
        logger.error(f"❌ Worker critical failure: {str(e)}")
        return {"status": "failed", "error": str(e)}