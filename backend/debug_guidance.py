import sys; sys.path.insert(0, ".")
from app.services.yfinance_client import _yf_quoteSummary
from app.services import finnhub_client

# 1. Yahoo Finance earningsTrend
data = _yf_quoteSummary("AAPL", "earnings,earningsTrend")
trend = data.get("earningsTrend", {}).get("trend", [])
for t in trend:
    period = t.get("period", "")
    end = t.get("endDate", "")
    ee = t.get("earningsEstimate", {})
    re = t.get("revenueEstimate", {})
    growth = t.get("growth", {})
    print(f"--- {period} (end: {end}) ---")
    eps_avg = ee.get("avg", {}).get("raw", "N/A") if isinstance(ee.get("avg"), dict) else "N/A"
    rev_avg = re.get("avg", {}).get("raw", "N/A") if isinstance(re.get("avg"), dict) else "N/A"
    rev_low = re.get("low", {}).get("raw", "N/A") if isinstance(re.get("low"), dict) else "N/A"
    rev_high = re.get("high", {}).get("raw", "N/A") if isinstance(re.get("high"), dict) else "N/A"
    growth_val = growth.get("raw", "N/A") if isinstance(growth, dict) else "N/A"
    print(f"  EPS est avg: {eps_avg}")
    print(f"  Rev est avg: {rev_avg}, low: {rev_low}, high: {rev_high}")
    print(f"  Growth: {growth_val}")

# 2. Finnhub revenue estimates
print("\n=== Finnhub Revenue Estimates ===")
try:
    import finnhub
    from app.config import FINNHUB_API_KEY
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    rev_est = client.company_revenue_estimates("AAPL", freq="quarterly")
    if rev_est and rev_est.get("data"):
        for item in rev_est["data"][:4]:
            print(f"  Period: {item.get('period')}, Avg: {item.get('revenueAvg')}, Actual: {item.get('revenueActual')}")
except Exception as e:
    print(f"  Error: {e}")

# 3. Finnhub company earnings (has revenue surprise?)
print("\n=== Finnhub Earnings (revenue fields?) ===")
earnings = finnhub_client.get_earnings_surprises("AAPL")
if earnings:
    print(f"  Keys in first item: {list(earnings[0].keys())}")
    print(f"  First item: {earnings[0]}")
