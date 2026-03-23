from app.config import CLAUDE_API_KEY

class AIClient:
    def __init__(self):
        self.enabled = bool(CLAUDE_API_KEY)
        self._client = None

    def _get_client(self):
        if self._client is None and self.enabled:
            import anthropic
            self._client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        return self._client

    def analyze_stock(self, ticker: str, overview: dict, financials: dict, recent_news: list) -> dict:
        if not self.enabled:
            return {
                "status": "disabled",
                "message": ".env 파일에 CLAUDE_API_KEY를 추가하면 AI 분석이 활성화됩니다.",
            }
        try:
            client = self._get_client()
            news_text = "\n".join([f"- {a['title']} ({a['published_at'][:10]})" for a in recent_news[:5]])
            prompt = f"""다음 종목에 대해 간결한 투자 리서치 요약을 한국어로 작성해주세요.

종목: {ticker} ({overview.get('name', '')})
섹터: {overview.get('sector', '-')}
현재가: ${overview.get('current_price', '-')}
PER: {overview.get('pe_ratio', '-')}
시가총액: {overview.get('market_cap', '-')}

최근 뉴스:
{news_text}

다음 항목을 포함해주세요:
1. 비즈니스 요약 (2~3줄)
2. 현재 밸류에이션 평가
3. 주요 리스크 요인
4. 주요 기회 요인
5. 전반적인 투자 견해 (중립적으로)"""

            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return {
                "status": "success",
                "analysis": message.content[0].text,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def analyze_macro(self, market_state: dict) -> dict:
        if not self.enabled:
            return {
                "status": "disabled",
                "message": ".env 파일에 CLAUDE_API_KEY를 추가하면 AI 분석이 활성화됩니다.",
            }
        try:
            client = self._get_client()
            metrics = market_state.get("metrics", {})
            prompt = f"""현재 미국 거시경제 지표를 바탕으로 시장 분석을 한국어로 작성해주세요.

지표:
- 시장 상태: {market_state.get('state', '-')}
- GDP 성장률(QoQ): {metrics.get('gdp_growth_qoq', '-')}%
- 실업률: {metrics.get('unemployment', '-')}%
- CPI YoY: {metrics.get('cpi_yoy', '-')}%
- 기준금리: {metrics.get('fed_rate', '-')}%

다음을 포함해주세요:
1. 현재 경기 사이클 위치 분석
2. 주요 거시 리스크
3. 투자자 관점에서 주목할 점
(3~5문단, 중립적 관점)"""

            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return {
                "status": "success",
                "analysis": message.content[0].text,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

ai_client = AIClient()
