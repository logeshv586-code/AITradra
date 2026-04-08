import pandas as pd
import numpy as np
from tools.indicator_service import IndicatorService

def test_indicators():
    # Create sample data
    data = {
        'open': np.random.uniform(100, 200, 100),
        'high': np.random.uniform(200, 300, 100),
        'low': np.random.uniform(50, 100, 100),
        'close': np.random.uniform(100, 200, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    }
    df = pd.DataFrame(data)
    
    # Compute indicators
    print("Computing indicators...")
    indicators = IndicatorService.get_latest_indicators(df)
    
    print("\nLatest Indicator Values:")
    for k, v in indicators.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    try:
        test_indicators()
    except Exception as e:
        print(f"Error during test: {e}")
