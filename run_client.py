import httpx
import time
import sys

def test_audit_flow(ticker: str):
    base_url = "http://localhost:8000/api/v1"
    print(f"\n🚀 [1/3] Triggering Enterprise Audit for {ticker}...")
    
    try:
        post_response = httpx.post(f"{base_url}/audit", json={"ticker": ticker})
        post_response.raise_for_status()
        
        task_id = post_response.json().get("task_id")
        print(f"🎫 [2/3] Order received! Task ID: {task_id}")
        print("⏳ [3/3] Waiting for Chef to finish cooking...\n")
        
        while True:
            get_response = httpx.get(f"{base_url}/audit/{task_id}")
            data = get_response.json()
            status = data.get("status")
            
            if status == "SUCCESS":
                print("\n==================================================")
                print(f"🏢 FINAL AUDIT REPORT: {ticker}")
                print("==================================================")
                
                result_data = data.get("result", {})
                if isinstance(result_data, dict) and "report" in result_data:
                    print(result_data["report"])
                else:
                    print("⚠️ RAW API PAYLOAD (Missing 'report' key):")
                    print(result_data)
                    
                print("==================================================\n")
                break
            elif status == "FAILURE":
                print(f"\n❌ AUDIT FAILED (Celery Error): {data.get('error', 'Unknown')}")
                break
            
            sys.stdout.write("▓ ")
            sys.stdout.flush()
            time.sleep(2)
            
    except Exception as e:
        print(f"\n❌ HTTP/Client Error: {str(e)}")

if __name__ == "__main__":
    # --- DYNAMIC INPUT FIX ---
    # If the user types a ticker in the terminal, use it. Otherwise, default to MSFT.
    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    test_audit_flow(ticker_arg)