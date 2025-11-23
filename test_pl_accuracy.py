"""
Test P/L Accuracy for TCS
Compares our calculation with expected values
"""
import sys
sys.path.insert(0, '.')

from app import get_timeframe_pl

print("=" * 70)
print("TCS P/L ACCURACY TEST")
print("=" * 70)

# Test TCS 1Y P/L
symbol = "TCS.NS"
timeframe = "1Y"

print(f"\nTesting {symbol} for {timeframe} period...")
result = get_timeframe_pl(symbol, timeframe)

if result:
    print(f"\n[OK] P/L Calculation Successful")
    print(f"\nStart Date: {result['start_date']}")
    print(f"Start Price: Rs.{result['start_price']:,.2f}")
    print(f"Current Price: Rs.{result['current_price']:,.2f}")
    print(f"Change: Rs.{result['change']:,.2f}")
    print(f"Change %: {result['change_pct']:.2f}%")
    print(f"Data Quality: {result.get('data_quality', 'unknown')}")
    
    # Compare with Google Finance (approximately -27%)
    expected_range = (-30, -20)  # Allow margin
    actual = result['change_pct']
    
    print(f"\n" + "=" * 70)
    print("ACCURACY VALIDATION")
    print("=" * 70)
    print(f"Expected Range (based on Google): {expected_range[0]}% to {expected_range[1]}%")
    print(f"Actual (Our App): {actual:.2f}%")
    
    if expected_range[0] <= actual <= expected_range[1]:
        print("\n[PASS] P/L calculation is within acceptable range")
    else:
        print(f"\n[WARNING] P/L is outside expected range")
        print(f"   Difference from -27%: {abs(-27 - actual):.2f}%")
else:
    print("\n[FAIL] Unable to calculate P/L")

# Test all timeframes
print("\n" + "=" * 70)
print("TESTING ALL TIMEFRAMES")
print("=" * 70)

timeframes = ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y", "Max"]

for tf in timeframes:
    result = get_timeframe_pl(symbol, tf)
    if result:
        print(f"\n{tf:5s}: {result['change_pct']:7.2f}% | Start: {result['start_date'].strftime('%Y-%m-%d')} | Quality: {result.get('data_quality', 'N/A')}")
    else:
        print(f"\n{tf:5s}: [FAILED]")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)

