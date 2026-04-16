import asyncio
import yfinance as yf
from typing import List, Dict, Any
from src.core.config import logger
from src.services.base import BaseAuditDataSource

class UnifiedMarketDataService(BaseAuditDataSource):
    """
    Enterprise Data Ingestion Layer.
    Pulls deep, pre-cleaned financial metrics required for comprehensive auditing.
    """
    
    async def _fetch_deep_financials(self, ticker: str) -> List[Dict[str, Any]]:
        logger.info(f"📊 Pulling deep financial profile for {ticker}...")
        try:
            # Run blocking yfinance calls in a background thread to keep async fast
            stock = yf.Ticker(ticker)
            info = await asyncio.to_thread(lambda: stock.info)
            
            if not info or 'shortName' not in info:
                logger.warning(f"No financial profile found for {ticker}.")
                return []

            # 1. Top-Line
            total_revenue = info.get('totalRevenue', 'DATA UNAVAILABLE')
            rev_growth = info.get('revenueGrowth', 'DATA UNAVAILABLE')
            
            # 2. Profitability
            net_income = info.get('netIncomeToCommon', 'DATA UNAVAILABLE')
            gross_margin = info.get('grossMargins', 'DATA UNAVAILABLE')
            op_margin = info.get('operatingMargins', 'DATA UNAVAILABLE')
            
            # 3. Liquidity
            total_cash = info.get('totalCash', 'DATA UNAVAILABLE')
            total_debt = info.get('totalDebt', 'DATA UNAVAILABLE')
            current_ratio = info.get('currentRatio', 'DATA UNAVAILABLE')
            
            # 4. Valuation
            market_cap = info.get('marketCap', 'DATA UNAVAILABLE')
            pe_ratio = info.get('trailingPE', 'DATA UNAVAILABLE')
            beta = info.get('beta', 'DATA UNAVAILABLE')

            # Build a structured, hyper-dense context string for the AI Analyst
            content_str = (
                f"ENTITY: {info.get('shortName', ticker)} ({ticker})\n"
                f"SECTOR: {info.get('sector', 'N/A')} | INDUSTRY: {info.get('industry', 'N/A')}\n"
                f"===================================\n"
                f"1. TOP-LINE PERFORMANCE\n"
                f"Total Revenue: {total_revenue}\n"
                f"Revenue Growth (YoY): {rev_growth}\n"
                f"-----------------------------------\n"
                f"2. PROFITABILITY\n"
                f"Net Income: {net_income}\n"
                f"Gross Margin: {gross_margin}\n"
                f"Operating Margin: {op_margin}\n"
                f"-----------------------------------\n"
                f"3. LIQUIDITY & BALANCE SHEET\n"
                f"Total Cash: {total_cash}\n"
                f"Total Debt: {total_debt}\n"
                f"Current Ratio: {current_ratio}\n"
                f"-----------------------------------\n"
                f"4. MARKET VALUATION\n"
                f"Market Cap: {market_cap}\n"
                f"P/E Ratio: {pe_ratio}\n"
                f"Beta (Volatility): {beta}\n"
                f"===================================\n"
                f"COMPANY SUMMARY: {info.get('longBusinessSummary', 'N/A')[:1000]}..." # Truncated to save tokens
            )

            documents = [{
                "content": content_str, 
                "metadata": {"ticker": ticker.upper(), "type": "Deep_Financial_Profile"}
            }]
            
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching global market data for {ticker}: {str(e)}")
            raise

    async def fetch_documents(self, ticker: str, limit: int = 1) -> List[Dict[str, Any]]:
        """Unified router. Feeds clean data for all tickers to the LangGraph agents."""
        return await self._fetch_deep_financials(ticker)

# Export singleton
sec_service = UnifiedMarketDataService()