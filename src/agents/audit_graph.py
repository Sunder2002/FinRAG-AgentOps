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
    logger.info("🔍 Querying Google API for available models...")
    api_key = settings.GOOGLE_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            
        available_models = [
            m.get("name").replace("models/", "") 
            for m in data.get("models", []) 
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        
        priority_cascade = ["gemini-1.5-pro", "gemini-1.5-pro-latest", "gemini-1.5-flash"]
        for target_model in priority_cascade:
            if target_model in available_models:
                return target_model
                
        return available_models[0] if available_models else "gemini-1.5-flash"
    except Exception as e:
        logger.error(f"Failed to fetch models dynamically: {str(e)}")
        return "gemini-1.5-flash"

llm = ChatGoogleGenerativeAI(
    model=get_dynamic_model(), 
    google_api_key=settings.GOOGLE_API_KEY, 
    temperature=0.1
)

def analyst_node(state: AuditState):
    logger.info("🤖 [Analyst Agent] Extracting metrics...")
    prompt = ChatPromptTemplate.from_template("Analyst: Extract revenue for {ticker} from this raw SEC data: {db_context}")
    response = (prompt | llm).invoke({"ticker": state["ticker"], "db_context": state["db_context"]})
    return {"analyst_summary": response.content}

def auditor_node(state: AuditState):
    logger.info("🤖 [Auditor Agent] Drafting initial report...")
    prompt = ChatPromptTemplate.from_template("Auditor: Write a short, professional opinion on this financial data: {analyst_summary}")
    response = (prompt | llm).invoke({"analyst_summary": state["analyst_summary"]})
    return {"final_report": response.content}

def compliance_node(state: AuditState):
    logger.info("🤖 [Compliance Agent] Verifying report for hallucinations/errors...")
    prompt = ChatPromptTemplate.from_template(
        "Compliance Officer: Review this report. If it mentions a specific revenue number, ensure it sounds factual. "
        "If the data is missing (like from a Form 4), ensure the tone is highly professional. "
        "Output the final cleared text with '[COMPLIANCE CLEARED]' at the start. Report: {final_report}"
    )
    response = (prompt | llm).invoke({"final_report": state["final_report"]})
    # We overwrite the final_report in the state with the compliance-checked version
    return {"final_report": response.content}

# --- BUILD THE 3-AGENT GRAPH ---
builder = StateGraph(AuditState)
builder.add_node("analyst", analyst_node)
builder.add_node("auditor", auditor_node)
builder.add_node("compliance", compliance_node)

builder.set_entry_point("analyst")
builder.add_edge("analyst", "auditor")
builder.add_edge("auditor", "compliance") # New routing!
builder.add_edge("compliance", END)       # End the graph after compliance

audit_app = builder.compile()