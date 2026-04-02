import time
import requests
import statistics

API_BASE = "http://localhost:8000"
ENDPOINTS = [
    "/api/market/watchlist",
    "/api/agents/status",
    "/api/stock/RELIANCE",
    "/api/market/indices"
]

def test_performance(iterations=5):
    print(f"🚀 Starting API Performance Test (Iterations: {iterations})")
    print("-" * 60)
    
    results = {e: [] for e in ENDPOINTS}
    
    for i in range(iterations):
        print(f"Iteration {i+1}...")
        for endpoint in ENDPOINTS:
            try:
                start = time.perf_counter()
                response = requests.get(f"{API_BASE}{endpoint}", timeout=10)
                elapsed = time.perf_counter() - start
                
                if response.status_code == 200:
                    results[endpoint].append(elapsed)
                else:
                    print(f"  ❌ {endpoint}: Status {response.status_code}")
            except Exception as e:
                print(f"  ❌ {endpoint}: Error {e}")
        time.sleep(1)

    print("\n📊 Summary (Response Times in Seconds):")
    print(f"{'Endpoint':<30} | {'Min':<8} | {'Max':<8} | {'Avg':<8}")
    print("-" * 60)
    
    for endpoint, times in results.items():
        if times:
            print(f"{endpoint:<30} | {min(times):.4f} | {max(times):.4f} | {statistics.mean(times):.4f}")
        else:
            print(f"{endpoint:<30} | N/A      | N/A      | N/A")

if __name__ == "__main__":
    test_performance()
