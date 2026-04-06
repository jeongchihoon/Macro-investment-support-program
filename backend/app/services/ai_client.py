"""AI 분석 클라이언트 — Gemini 통일

종목 종합 분석과 거시경제 분석을 Gemini로 수행.
Claude API 의존 제거 → Gemini 2.5-flash-lite로 비용 최소화.
"""

import requests
import json
from app.config import GOOGLE_API_KEY

GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


class AIClient:
    def __init__(self):
        self.enabled = bool(GOOGLE_API_KEY)

    def _call_gemini(self, prompt: str, max_tokens: int = 1024) -> str | None:
        if not self.enabled:
            return None
        try:
            resp = requests.post(
                f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": max_tokens,
                    },
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None

    def analyze_stock(self, ticker: str, overview: dict, financials: dict, recent_news: list) -> dict:
        if not self.enabled:
            return {"status": "disabled", "message": "GOOGLE_API_KEY 필요"}

        news_text = "\n".join([f"- {a['title']}" for a in recent_news[:5]])

        prompt = f"""[역할] 종목 투자 리서치 애널리스트. 밸류에이션·리스크·기회를 균형있게 분석.

[대상] {ticker} ({overview.get('name','')}) | {overview.get('sector','-')}
현재가: ${overview.get('current_price','-')} | PER: {overview.get('pe_ratio','-')} | 시총: {overview.get('market_cap','-')}

[최근 뉴스]
{news_text}

[출력] 한국어. 간결하게 5개 항목:
1. 비즈니스 요약 (2줄)
2. 밸류에이션 평가
3. 주요 리스크
4. 주요 기회
5. 투자 견해 (중립적)"""

        result = self._call_gemini(prompt)
        if result:
            return {"status": "success", "analysis": result}
        return {"status": "error", "message": "분석 실패"}

    def analyze_macro(self, market_state: dict) -> dict:
        if not self.enabled:
            return {"status": "disabled", "message": "GOOGLE_API_KEY 필요"}

        metrics = market_state.get("metrics", {})

        prompt = f"""[역할] 거시경제 전략가. 경기 사이클 위치와 투자 시사점을 분석.

[지표]
상태: {market_state.get('state','-')} | GDP(QoQ): {metrics.get('gdp_growth_qoq','-')}%
실업률: {metrics.get('unemployment','-')}% | CPI(YoY): {metrics.get('cpi_yoy','-')}%
기준금리: {metrics.get('fed_rate','-')}%

[출력] 한국어. 3-4문단:
1. 현재 경기 사이클 위치
2. 주요 거시 리스크
3. 투자자 관점 주목점"""

        result = self._call_gemini(prompt, max_tokens=800)
        if result:
            return {"status": "success", "analysis": result}
        return {"status": "error", "message": "분석 실패"}


ai_client = AIClient()
