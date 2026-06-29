# FinVision - 개인 투자 리서치 대시보드

## 설치 및 실행

### 1. 패키지 설치
```bash
# 백엔드
cd backend
pip install -r requirements.txt

# 프론트엔드
cd frontend
npm install
```

### 2. API 키 설정
`.env` 파일을 열고 키를 입력하세요:
```
NEWS_API_KEY=      # newsapi.org 에서 무료 발급
FRED_API_KEY=      # fred.stlouisfed.org 에서 무료 발급 (없어도 기본 동작)
GEMINI_API_KEY=    # aistudio.google.com — 가이던스 분석, 번역, 심층 리서치 등 AI 기능 전체
FINNHUB_API_KEY=   # finnhub.io — 실적 발표 시뮬레이터
# 심층 리서치 검색 품질 향상 (선택)
TAVILY_API_KEY=
PARALLEL_API_KEY=
```

### 3. 실행
터미널 2개를 열어서:

**터미널 1 (백엔드):**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**터미널 2 (프론트엔드):**
```bash
cd frontend
npm run dev
```

### 4. 브라우저에서 열기
http://localhost:5173

---

## 기능

| 탭 | 기능 |
|---|---|
| 거시경제 | GDP, 실업률, CPI, 금리 차트 + 시장 상태 판단 + 유망 섹터 표시 + Gemini AI 거시분석 |
| 종목 분석 | 티커 검색 → 주가 차트 + 재무제표 + SEC 공시 + 뉴스 + 경쟁사/핵심지표 AI 선정 |
| 실적 분석 | 어닝 서프라이즈 히스토리 + 가이던스 AI 분석 (Gemini) + 애널리스트 vs AI 비교 |
| 심층 리서치 | Gemini + 다중 검색소스 기반 멀티에이전트 리서치 (Planner→Critic→Synthesizer) |
| 포트폴리오 | 매수 종목 추가/삭제 + 수익률 + 종목별 상세 정보 |

## AI 기능 (Gemini 기반)
> Claude API는 사용하지 않습니다. 모든 AI 기능은 **Google Gemini** 기반입니다.

- **가이던스 분석**: SEC 8-K 프레스 릴리스 → Gemini가 경영진 가이던스/테마/감성 분석
- **경쟁사/핵심지표 자동 선정**: 종목별 맞춤 경쟁사 및 KPI를 Gemini가 추출
- **기업 소개 번역**: 영문 → 한국어 (Gemini, MD5 캐시)
- **심층 리서치 채팅**: 멀티에이전트 파이프라인 (Flash Planner → Critic 루프 → Pro Synthesizer)

## 데이터 소스
- **거시경제**: FRED API (미연방준비제도)
- **주가/재무제표**: Yahoo Finance (yfinance)
- **공시**: SEC EDGAR API
- **뉴스**: NewsAPI (무료 100콜/일)
- **실적**: Finnhub, Alpha Vantage
- **심층 리서치 검색**: Tavily, Parallel.ai, SEC EDGAR, FRED, arXiv
