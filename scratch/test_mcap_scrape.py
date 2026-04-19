import httpx
import re

def test_scrape(ticker):
    print(f"Testing fallback scrape for {ticker}...")
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                mcap_match = re.search(r'>Market Cap</span>.*?<span.*?>(.*?)</span>', resp.text)
                if mcap_match:
                    print(f"Found Market Cap: {mcap_match.group(1)}")
                    return True
                else:
                    print("Could not find Market Cap in HTML")
            else:
                print(f"Failed with status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    test_scrape("AAPL")
    test_scrape("BTC-USD")
