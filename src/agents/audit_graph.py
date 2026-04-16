import time
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

FALLBACK_CASCADE = [
    "gemini-2.5-flash",       
    "gemini-2.5-flash-lite",  
    "gemini-3.1-flash-lite"   
]

def resilient_invoke(prompt_template: ChatPromptTemplate, kwargs: dict, context_key: str = None) -> str:
    current_context = kwargs.get(context_key, "") if context_key else ""
    
    for attempt, model_name in enumerate(FALLBACK_CASCADE):
        try:
            logger.info(f"🔄 [Attempt {attempt+1}] Routing to {model_name}...")
            
            if attempt > 0 and context_key and len(current_context) > 2000:
                current_context = current_context[:int(len(current_context) * 0.6)]
                kwargs[context_key] = current_context
                logger.warning(f"📉 Squeezing context size to {len(current_context)} chars.")

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.0, # PRODUCTION FIX: Set to 0.0 for absolute factual extraction (no creativity)
                max_retries=0 
            )
            
            chain = prompt_template | llm
            response = chain.invoke(kwargs)
            logger.info(f"✅ Success using {model_name}!")
            return response.content
            
        except Exception as e:
            logger.warning(f"⚠️ {model_name} failed: {str(e)[:80]}...")
            time.sleep(3) 
            
    logger.error("❌ ALL models in the cascade failed.")
    return "[SYSTEM WARNING] API capacity limits reached."


def analyst_node(state: AuditState):
    logger.info("🤖 [Analyst Agent] Extracting comprehensive metrics...")
    initial_safe_context = str(state.get("db_context", ""))[:12000]
    
    # PRODUCTION FIX: Strict Persona & Structured Extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Senior Equity Analyst. Your job is to extract structured financial metrics from messy data dumps. If a specific metric is missing, explicitly write 'DATA UNAVAILABLE'. DO NOT hallucinate numbers."),
        ("user", """Extract a comprehensive financial profile for {ticker} from this raw data:
        {db_context}

        REQUIRED METRICS:
        1. Top-Line (Total Revenue, YoY Growth if available)
        2. Profitability (Net Income, Gross Margin, Operating Margin)
        3. Liquidity (Total Cash, Total Debt)
        4. Valuation (Market Cap, P/E Ratio, Beta)

        Format the output as a clean, bulleted markdown list.""")
    ])
    
    result = resilient_invoke(prompt, {"ticker": state["ticker"], "db_context": initial_safe_context}, context_key="db_context")
    return {"analyst_summary": result}

def auditor_node(state: AuditState):
    logger.info("🤖 [Auditor Agent] Drafting initial report...")
    time.sleep(4) 
    
    # PRODUCTION FIX: Framework-Driven Analysis
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Lead Financial Auditor. Provide a critical, objective assessment based ONLY on the provided analyst summary. Do not invent outside knowledge."),
        ("user", """Draft a formal, professional Audit Opinion based on these metrics:
        {analyst_summary}

        REQUIRED REPORT STRUCTURE:
        ## Executive Summary
        (2-sentence overview of the financial posture)
        
        ## Assessment of Profitability
        (Analyze the margins and net income. Are they healthy?)
        
        ## Assessment of Risk & Liquidity
        (Assess the debt-to-cash position and valuation risks)
        
        ## Final Audit Conclusion
        (Conclude if the financial posture appears robust, stable, or at-risk based strictly on available data.)""")
    ])
    
    result = resilient_invoke(prompt, {"analyst_summary": state["analyst_summary"]}, context_key="analyst_summary")
    return {"final_report": result}

def compliance_node(state: AuditState):
    logger.info("🤖 [Compliance Agent] Verifying report for hallucinations...")
    time.sleep(4) 
    
    # PRODUCTION FIX: Legal/Compliance Guardrails
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Chief Compliance Officer for a major bank. Your job is to ensure the report contains no definitive forward-looking guarantees and uses appropriate financial disclaimers."),
        ("user", """Review this auditor report:
        {final_report}

        COMPLIANCE RULES:
        1. Ensure no direct stock-buying or selling advice is given. If present, neutralize the language.
        2. Add a standard "Not Financial Advice" disclaimer at the very bottom.
        3. Prepend '[COMPLIANCE CLEARED]' to the very top.
        
        Return the finalized, sanitized report.""")
    ])
    
    result = resilient_invoke(prompt, {"final_report": state["final_report"]}, context_key="final_report")
    return {"final_report": result}

# --- BUILD THE 3-AGENT GRAPH ---
builder = StateGraph(AuditState)
builder.add_node("analyst", analyst_node)
builder.add_node("auditor", auditor_node)
builder.add_node("compliance", compliance_node)

builder.set_entry_point("analyst")
builder.add_edge("analyst", "auditor")
builder.add_edge("auditor", "compliance")
builder.add_edge("compliance", END)

audit_app = builder.compile()