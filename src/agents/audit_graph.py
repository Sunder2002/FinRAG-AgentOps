import httpx
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings, logger

class AuditState(TypedDict):
    ticker: str
    db_context: str
    analyst_summary: str
    final_report: str

def get_dynamic_model() -> str:
    """
    Dynamically queries the Google API for available models and selects
    the best one suited for complex financial reasoning.
    Bypasses SDK versioning issues by using the REST API directly.
    """
    logger.info("🔍 Querying Google API for available models...")
    api_key = settings.GOOGLE_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            
        # Filter for models that actually support text generation
        available_models = [
            m.get("name").replace("models/", "") 
            for m in data.get("models", []) 
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        
        # Priority cascade for an Enterprise Financial Audit:
        # 1. 1.5 Pro (State-of-the-art reasoning, best for financial data)
        # 2. 1.5 Flash (Extremely fast, highly capable fallback)
        # 3. 1.0 Pro (Legacy fallback if others are constrained)
        priority_cascade = [
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.0-pro"
        ]
        
        for target_model in priority_cascade:
            if target_model in available_models:
                logger.info(f"✅ Dynamically selected optimal model: {target_model}")
                return target_model
                
        # Absolute fallback if priority list fails but API is up
        fallback = available_models[0] if available_models else "gemini-1.5-flash"
        logger.warning(f"Priority models not found in registry. Falling back to: {fallback}")
        return fallback
        
    except Exception as e:
        logger.error(f"Failed to fetch models dynamically: {str(e)}. Defaulting to gemini-1.5-flash.")
        return "gemini-1.5-flash"

# Initialize LLM with the dynamically selected model
llm = ChatGoogleGenerativeAI(
    model=get_dynamic_model(), 
    google_api_key=settings.GOOGLE_API_KEY, 
    temperature=0.1
)

def analyst_node(state: AuditState):
    logger.info("🤖 [Analyst Agent] Extracting metrics...")
    prompt = ChatPromptTemplate.from_template("Analyst: Extract revenue for {ticker} from: {db_context}")
    # Pass inputs explicitly as a dictionary to avoid LangChain internal state parsing bugs
    response = (prompt | llm).invoke({"ticker": state["ticker"], "db_context": state["db_context"]})
    return {"analyst_summary": response.content}

def auditor_node(state: AuditState):
    logger.info("🤖 [Auditor Agent] Finalizing report...")
    prompt = ChatPromptTemplate.from_template("Auditor: Write 2-sentence opinion on: {analyst_summary}")
    response = (prompt | llm).invoke({"analyst_summary": state["analyst_summary"]})
    return {"final_report": response.content}

builder = StateGraph(AuditState)
builder.add_node("analyst", analyst_node)
builder.add_node("auditor", auditor_node)
builder.set_entry_point("analyst")
builder.add_edge("analyst", "auditor")
builder.add_edge("auditor", END)
audit_app = builder.compile()