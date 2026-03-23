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
NEWS_API_KEY=    # newsapi.org 에서 무료 발급
FRED_API_KEY=    # fred.stlouisfed.org 에서 무료 발급 (없어도 기본 동작)
CLAUDE_API_KEY=  # console.anthropic.com (없으면 AI 버튼 비활성)
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
| 거시경제 | GDP, 실업률, CPI, 금리 차트 + 시장 상태 판단 + 유망 섹터 표시 |
| 종목 분석 | 티커 검색 → 주가 차트 + 재무제표 + SEC 공시 + 뉴스 |
| 포트폴리오 | 매수 종목 추가/삭제 + 수익률 + 종목별 상세 정보 |

## 데이터 소스 (전부 무료)
- **거시경제**: FRED API (미연방준비제도)
- **주가/재무제표**: Yahoo Finance (yfinance)
- **공시**: SEC EDGAR API
- **뉴스**: NewsAPI (무료 100콜/일)
