import asyncio
from src.core.config import logger
from src.services.sec_service import sec_service
from src.services.vector_service import vector_manager
from src.agents.audit_graph import audit_app
from langchain_text_splitters import RecursiveCharacterTextSplitter

async def run_enterprise_audit(ticker: str):
    logger.info(f"--- 🚀 INITIATING AUDIT FOR {ticker} ---")
    
    # 1. DATA INGESTION (The Digital Intern)
    docs = await sec_service.fetch_documents(ticker)
    raw_text = docs[0]["content"]
    
    # 2. DATA CHUNKING (Optimizing for AI Context)
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_text(raw_text)
    
    # 3. VECTOR INDEXING (The Digital Filing Cabinet)
    vector_manager.upsert_documents(chunks, [{"ticker": ticker} for _ in chunks])
    
    # 4. KNOWLEDGE RETRIEVAL
    context = vector_manager.search("revenue growth")
    
    # 5. MULTI-AGENT REASONING
    initial_state = {
        "ticker": ticker,
        "db_context": context,
        "analyst_summary": "",
        "final_report": ""
    }
    
    logger.info("🧠 Handing off to the Multi-Agent Boardroom...")
    result = audit_app.invoke(initial_state)
    
    # 6. FINAL OUTPUT
    print("\n" + "="*60)
    print(f"🏢 FINAL AUDIT REPORT: {ticker}")
    print("="*60)
    print(result["final_report"])
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_enterprise_audit("MSFT"))