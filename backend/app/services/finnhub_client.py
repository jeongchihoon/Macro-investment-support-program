"""Finnhub API 클라이언트 — 어닝 서프라이즈 데이터 수집"""

import time
import threading
from app.config import FINNHUB_API_KEY

# ── Rate Limiting (분당 60회 → 최소 1초 간격) ──
_last_call = 0
_rate_lock = threading.Lock()


def _rate_limit():
    global _last_call
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_call = time.time()


_client = None


def _get_client():
    global _client
    if not _client and FINNHUB_API_KEY:
        try:
            import finnhub
            _client = finnhub.Client(api_key=FINNHUB_API_KEY)
        except ImportError:
            return None
    return _client


def is_available():
    """Finnhub API 키가 설정되어 있는지 확인"""
    return bool(FINNHUB_API_KEY)


def get_earnings_surprises(ticker: str) -> list:
    """어닝 서프라이즈 히스토리 (최대 100개 분기)

    Returns:
        list of dict: [{actual, estimate, period, quarter, surprise, surprisePercent, symbol, year}, ...]
    """
    client = _get_client()
    if not client:
        return []
    _rate_limit()
    for attempt in range(3):
        try:
            data = client.company_earnings(ticker.upper(), limit=100)
            return data or []
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)  # exponential backoff
            continue
    return []


def get_earnings_calendar(ticker: str) -> dict:
    """다음 실적 발표 예정일 조회

    Returns:
        dict: {earningsCalendar: [{date, epsActual, epsEstimate, ...}]}
    """
    client = _get_client()
    if not client:
        return {}
    _rate_limit()
    try:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        data = client.earnings_calendar(_from=today, to=future, symbol=ticker.upper())
        return data or {}
    except Exception:
        return {}


def get_eps_estimates(ticker: str) -> dict:
    """현재/다음 분기 EPS 컨센서스 추정치

    Returns:
        dict: {data: [{period, numberAnalysts, ...}], freq, symbol}
    """
    client = _get_client()
    if not client:
        return {}
    _rate_limit()
    try:
        data = client.company_eps_estimates(ticker.upper(), freq='quarterly')
        return data or {}
    except Exception:
        return {}
