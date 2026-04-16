import httpx
import time
import sys

def test_audit_flow(ticker: str):
    base_url = "http://localhost:8000/api/v1"
    print(f"\n🚀 [1/3] Triggering Enterprise Audit for {ticker}...")
    
    try:
        # Step 1: Send the order to the Waiter
        post_response = httpx.post(f"{base_url}/audit", json={"ticker": ticker})
        post_response.raise_for_status()
        
        task_id = post_response.json().get("task_id")
        print(f"🎫 [2/3] Order received! Task ID: {task_id}")
        print("⏳ [3/3] Waiting for Chef to finish cooking...\n")
        
        # Step 2: Automatically ask the Waiter if the food is ready every 2 seconds
        while True:
            get_response = httpx.get(f"{base_url}/audit/{task_id}")
            data = get_response.json()
            status = data.get("status")
            
            if status == "SUCCESS":
                print("==================================================")
                print(f"🏢 FINAL AUDIT REPORT: {ticker}")
                print("==================================================")
                print(data["result"]["report"])
                print("==================================================\n")
                break
            elif status == "FAILURE":
                print(f"❌ AUDIT FAILED: {data.get('result')}")
                break
            
            # Print a dot so we know it's thinking, without spamming the screen
            sys.stdout.write("▓ ")
            sys.stdout.flush()
            time.sleep(2)
            
    except Exception as e:
        print(f"\n❌ Client Error: {str(e)}")

if __name__ == "__main__":
    # Change this ticker to whatever you want, run the file, and watch it go.
    test_audit_flow("RELIANCE.NS")