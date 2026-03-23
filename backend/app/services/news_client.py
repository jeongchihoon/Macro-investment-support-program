import requests
from app.config import NEWS_API_KEY

def get_stock_news(ticker: str, company_name: str = "", limit: int = 10):
    if not NEWS_API_KEY:
        return {"error": "NEWS_API_KEY가 .env에 없습니다.", "articles": []}

    query = company_name or ticker
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for a in data.get("articles", []):
            articles.append({
                "title": a.get("title", ""),
                "source": a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": a.get("url", ""),
                "description": a.get("description", ""),
            })
        return {"articles": articles}
    except Exception as e:
        return {"error": str(e), "articles": []}

def get_macro_news(limit: int = 10):
    if not NEWS_API_KEY:
        return {"error": "NEWS_API_KEY가 .env에 없습니다.", "articles": []}

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "economy GDP inflation Federal Reserve interest rate",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for a in data.get("articles", []):
            articles.append({
                "title": a.get("title", ""),
                "source": a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": a.get("url", ""),
                "description": a.get("description", ""),
            })
        return {"articles": articles}
    except Exception as e:
        return {"error": str(e), "articles": []}
