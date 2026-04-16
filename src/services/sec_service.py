import asyncio
import httpx
import yfinance as yf
from typing import List, Dict, Any, Optional
from src.core.config import logger, settings
from src.services.base import BaseAuditDataSource

class SECRateLimitError(Exception):
    pass

class UnifiedMarketDataService(BaseAuditDataSource):
    """
    Enterprise Data Router. 
    Dynamically routes US tickers to the SEC EDGAR API, 
    and International/Indian tickers (.NS, .BO) to Yahoo Finance.
    """
    def __init__(self) -> None:
        # --- SEC EDGAR Configuration ---
        self.headers: Dict[str, str] = {
            "User-Agent": settings.SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate"
        }
        self.tickers_url: str = "https://www.sec.gov/files/company_tickers.json"
        self.base_submissions_url: str = "https://data.sec.gov/submissions/CIK"
        self._client_timeout: float = 15.0
        self._rate_limit: asyncio.Semaphore = asyncio.Semaphore(10)

    # ==========================================
    # ROUTE 1: US GOVERNMENT SEC EDGAR LOGIC
    # ==========================================
    async def _get_cik(self, client: httpx.AsyncClient, ticker: str) -> Optional[str]:
        logger.info(f"Resolving CIK for ticker: {ticker}")
        response = await client.get(self.tickers_url)
        response.raise_for_status()

        data: Dict[str, Any] = response.json()
        for item in data.values():
            if item.get("ticker") == ticker.upper():
                return str(item.get("cik_str")).zfill(10)
        return None

    async def _fetch_sec_data(self, ticker: str, limit: int) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(headers=self.headers, timeout=self._client_timeout, http2=True) as client:
            try:
                async with self._rate_limit:
                    cik: Optional[str] = await self._get_cik(client, ticker)
                    if not cik:
                        logger.warning(f"Ticker {ticker} not found in SEC database.")
                        return []

                    logger.info(f"Resolved {ticker} to CIK: {cik}. Fetching submissions...")
                    await asyncio.sleep(0.15) # Politeness delay for SEC limits

                    submission_url = f"{self.base_submissions_url}{cik}.json"
                    response = await client.get(submission_url)

                    if response.status_code == 429:
                        raise SECRateLimitError("SEC Rate Limit Exceeded.")
                    response.raise_for_status()

                    data: Dict[str, Any] = response.json()
                    recent_filings: Dict[str, list] = data.get("filings", {}).get("recent", {})

                    if not recent_filings:
                        return []

                    documents: List[Dict[str, Any]] = []
                    for i in range(min(limit, len(recent_filings.get("accessionNumber", [])))):
                        form: str = recent_filings["form"][i]
                        date: str = recent_filings["filingDate"][i]
                        desc: str = recent_filings["primaryDocDescription"][i]
                        
                        content_str = (
                            f"ENTITY: {data.get('name', ticker)}\n"
                            f"FORM TYPE: {form}\n"
                            f"FILING DATE: {date}\n"
                            f"DESCRIPTION: {desc}\n"
                            f"SEC RECORD: The entity officially filed a {form} document on {date}."
                        )

                        documents.append({
                            "content": content_str,
                            "metadata": {"ticker": ticker.upper(), "cik": cik, "form": form, "filing_date": date}
                        })
                    return documents
            except Exception as e:
                logger.error(f"Error in SEC fetch for {ticker}: {str(e)}")
                raise

    # ==========================================
    # ROUTE 2: GLOBAL/INDIAN MARKET LOGIC
    # ==========================================
    async def _fetch_global_data(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            # yfinance is synchronous, so we wrap it to keep the async loop healthy
            stock = yf.Ticker(ticker)
            income_stmt = await asyncio.to_thread(lambda: stock.income_stmt)
            
            if income_stmt is None or income_stmt.empty:
                logger.warning(f"No financial data found for {ticker}.")
                return []

            latest_date = income_stmt.columns[0]
            latest_data = income_stmt[latest_date]
            
            total_revenue = latest_data.get("Total Revenue", "N/A")
            net_income = latest_data.get("Net Income", "N/A")

            content_str = (
                f"ENTITY: {ticker}\n"
                f"REPORTING DATE: {latest_date.strftime('%Y-%m-%d')}\n"
                f"SOURCE: Audited Income Statement\n"
                f"--- FINANCIAL METRICS ---\n"
                f"Total Revenue: {total_revenue}\n"
                f"Net Income: {net_income}\n"
                f"-------------------------\n"
            )

            documents = [{"content": content_str, "metadata": {"ticker": ticker.upper(), "date": str(latest_date)}}]
            return documents
        except Exception as e:
            logger.error(f"Error fetching global market data for {ticker}: {str(e)}")
            raise

    # ==========================================
    # THE ROUTER (Strategy Pattern)
    # ==========================================
    async def fetch_documents(self, ticker: str, limit: int = 1) -> List[Dict[str, Any]]:
        """Determines which data source to use based on the ticker format."""
        if ticker.endswith('.NS') or ticker.endswith('.BO'):
            logger.info(f"🌐 [ROUTER] Indian Ticker detected. Routing to Global Finance API...")
            return await self._fetch_global_data(ticker)
        else:
            logger.info(f"🏛️ [ROUTER] US Ticker detected. Routing to Government SEC API...")
            return await self._fetch_sec_data(ticker, limit)

# Export as sec_service so main.py and celery_worker.py don't break
sec_service = UnifiedMarketDataService()