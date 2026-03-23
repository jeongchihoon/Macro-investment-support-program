from fastapi import APIRouter, HTTPException
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services import yfinance_client
from app.services.stock_dictionary import search_local
from app.services.sec_client import get_filings
from app.services.news_client import get_stock_news
from app.services.ai_client import ai_client

router = APIRouter(prefix="/api/stock", tags=["stock"])

_chart_pool = ThreadPoolExecutor(max_workers=6)


def _enrich_with_chart(item: dict) -> dict:
    ticker = item["ticker"]
    try:
        chart = yfinance_client._yf_chart(ticker, interval="1d", range_="5d", timeout=5)
        if chart:
            chart_result = chart.get("chart", {}).get("result", [])
            if chart_result:
                meta = chart_result[0].get("meta", {})
                closes = chart_result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_closes = [c for c in closes if c is not None]
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("chartPreviousClose") or (valid_closes[0] if valid_closes else None)
                change_pct = None
                if price and prev_close and prev_close != 0:
                    change_pct = round((price - prev_close) / prev_close * 100, 2)
                sparkline = [round(c, 2) for c in valid_closes[-5:]] if valid_closes else []
                item["price"] = round(price, 2) if price else None
                item["change_pct"] = change_pct
                item["sparkline"] = sparkline
                return item
    except Exception:
        pass
    item["price"] = None
    item["change_pct"] = None
    item["sparkline"] = []
    return item


@router.get("/search")
def search(q: str):
    results = yfinance_client.search_ticker(q)
    return {"results": results}


@router.get("/suggest")
def suggest(q: str, enrich: int = 0):
    """검색 제안. enrich=0이면 즉시 반환, enrich=1이면 차트 데이터 포함"""
    if not q or not q.strip():
        return {"results": []}

    query = q.strip()

    # 1단계: 로컬 사전 검색 (즉시 반환, 한국어/초성/오타 지원)
    local_results = search_local(query, max_results=6)

    # 2단계: Yahoo 검색 — 로컬 결과가 부족하면 항상 Yahoo에서 보충
    yahoo_results = []
    if len(local_results) < 3:
        try:
            yahoo_results = yfinance_client.search_ticker(query)
        except Exception:
            pass

    # 3단계: 결과 합치기 (정확 매칭 로컬 → Yahoo → 퍼지 로컬)
    seen_tickers = set()
    merged = []
    query_upper = query.upper()

    # 로컬 결과를 정확 매칭 vs 퍼지 매칭으로 분리
    exact_local = []
    fuzzy_local = []
    for item in local_results:
        t = item["ticker"]
        name_lower = item.get("name", "").lower()
        # 티커 정확 일치 또는 이름에 검색어 포함이면 정확 매칭
        if t == query_upper or query.lower() in name_lower or query.lower() in t.lower():
            exact_local.append(item)
        else:
            fuzzy_local.append(item)

    # 정확 매칭 로컬 먼저
    for item in exact_local:
        t = item["ticker"]
        if t not in seen_tickers:
            seen_tickers.add(t)
            merged.append({
                "ticker": t,
                "name": item["name"],
                "exchange": "",
                "sector": "",
            })

    # Yahoo 결과 (미국 주식만, .MX 등 제외)
    for item in yahoo_results:
        t = item["ticker"]
        if "." in t:  # 외국 거래소 제외
            continue
        if t not in seen_tickers:
            seen_tickers.add(t)
            merged.append(item)
        else:
            for m in merged:
                if m["ticker"] == t:
                    if item.get("exchange"):
                        m["exchange"] = item["exchange"]
                    if item.get("sector"):
                        m["sector"] = item["sector"]
                    break

    # 퍼지 로컬 (비슷한 이름)
    for item in fuzzy_local:
        t = item["ticker"]
        if t not in seen_tickers:
            seen_tickers.add(t)
            merged.append({
                "ticker": t,
                "name": item["name"],
                "exchange": "",
                "sector": "",
            })

    # 상위 5개만
    merged = merged[:5]

    if not merged:
        return {"results": []}

    # enrich=0 → 차트 없이 즉시 반환 (드롭다운 빠른 표시용)
    if not enrich:
        for item in merged:
            item.setdefault("price", None)
            item.setdefault("change_pct", None)
            item.setdefault("sparkline", [])
        return {"results": merged}

    # enrich=1 → 차트 데이터 병렬 요청 (상위 4개만)
    to_enrich = merged[:4]
    no_enrich = merged[4:]

    futures = {_chart_pool.submit(_enrich_with_chart, item): item for item in to_enrich}
    enriched = []
    for future in as_completed(futures):
        try:
            enriched.append(future.result())
        except Exception:
            enriched.append(futures[future])

    for item in no_enrich:
        item["price"] = None
        item["change_pct"] = None
        item["sparkline"] = []
        enriched.append(item)

    order = {item["ticker"]: i for i, item in enumerate(merged)}
    enriched.sort(key=lambda x: order.get(x["ticker"], 99))

    return {"results": enriched}


@router.get("/{ticker}/overview")
def overview(ticker: str):
    try:
        return yfinance_client.get_overview(ticker)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{ticker}/quote")
def quote(ticker: str):
    """실시간 가격만 경량으로 반환 (30초 자동 갱신용)"""
    try:
        chart = yfinance_client._yf_chart(ticker, interval="1d", range_="1d")
        if not chart:
            raise HTTPException(status_code=404, detail="No data")
        result = chart.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        return {
            "ticker": ticker.upper(),
            "current_price": meta.get("regularMarketPrice"),
            "previous_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
            "market_time": meta.get("regularMarketTime"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/price")
def price(ticker: str, period: str = "1y"):
    valid_periods = ["1d", "3d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "3y", "5y", "10y", "max"]
    if period not in valid_periods:
        period = "1y"
    data = yfinance_client.get_price_history(ticker, period)
    return {"ticker": ticker, "period": period, "data": data}

@router.get("/{ticker}/financials")
def financials(ticker: str):
    return yfinance_client.get_financials(ticker)

@router.get("/{ticker}/metric-history")
def metric_history(ticker: str):
    """주요 재무 지표의 연도별 히스토리 반환 (차트용)"""
    try:
        return yfinance_client.get_metric_history(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/filings")
def filings(ticker: str):
    data = get_filings(ticker)
    return {"ticker": ticker, "filings": data}

@router.get("/{ticker}/news")
def news(ticker: str):
    from app.services.stock_dictionary import STOCK_DB
    company_name = ticker.upper()
    for t, name, kr_names in STOCK_DB:
        if t == ticker.upper():
            company_name = name
            break
    return get_stock_news(ticker, company_name, limit=15)

@router.post("/{ticker}/ai-analyze")
def ai_analyze(ticker: str):
    try:
        overview = yfinance_client.get_overview(ticker)
        financials = yfinance_client.get_financials(ticker)
        news_data = get_stock_news(ticker, overview.get("name", ticker), limit=5)
        return ai_client.analyze_stock(ticker, overview, financials, news_data.get("articles", []))
    except Exception as e:
        return {"status": "error", "message": str(e)}
