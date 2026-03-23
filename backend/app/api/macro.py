from fastapi import APIRouter
from app.services import fred_client
from app.services.news_client import get_macro_news
from app.services.ai_client import ai_client

router = APIRouter(prefix="/api/macro", tags=["macro"])

@router.get("/overview")
def macro_overview():
    indicators = {}
    for key, meta in fred_client.INDICATORS.items():
        val, date = fred_client.get_latest_value(key)
        indicators[key] = {
            "name": meta["name"],
            "unit": meta["unit"],
            "value": val,
            "date": date,
        }
    return {"indicators": indicators}

@router.get("/indicator/{series_id}")
def macro_indicator(series_id: str, limit: int = 60):
    meta = fred_client.INDICATORS.get(series_id, {"name": series_id, "unit": ""})
    data = fred_client.fetch_series(series_id, limit=limit)
    return {"series_id": series_id, "name": meta["name"], "unit": meta["unit"], "data": data}

@router.get("/market-state")
def market_state():
    return fred_client.get_market_state()

@router.get("/news")
def macro_news():
    return get_macro_news(limit=10)

@router.post("/ai-analyze")
def ai_analyze_macro():
    state = fred_client.get_market_state()
    return ai_client.analyze_macro(state)
