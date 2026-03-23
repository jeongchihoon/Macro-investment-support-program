"""Gemini AI 기반 가이던스 분석 서비스

어닝콜 트랜스크립트 (Motley Fool) + SEC EDGAR 8-K를 Gemini로 분석하여
가이던스 요약, 핵심 테마, 감성 점수 등을 추출.
- 1순위: Motley Fool 어닝콜 트랜스크립트 (CEO/CFO 발언 + 애널리스트 Q&A)
- 2순위: SEC 8-K 프레스 릴리스 (폴백)
결과는 DB에 영구 캐싱 (과거 가이던스는 변하지 않음).
"""

import aiosqlite
import asyncio
import json
import logging
import re
import requests
from datetime import datetime

from app.config import GOOGLE_API_KEY
from app.database import DB_PATH

logger = logging.getLogger(__name__)

# ── 종목명 매핑 (Motley Fool URL용) ──
# ticker → company name slug
_COMPANY_SLUGS = {
    "AAPL": "apple", "MSFT": "microsoft", "GOOGL": "alphabet", "GOOG": "alphabet",
    "AMZN": "amazon", "META": "meta-platforms", "TSLA": "tesla", "NVDA": "nvidia",
    "NFLX": "netflix", "AMD": "advanced-micro-devices", "INTC": "intel",
    "CRM": "salesforce", "ORCL": "oracle", "ADBE": "adobe", "CSCO": "cisco-systems",
    "QCOM": "qualcomm", "TXN": "texas-instruments", "AVGO": "broadcom",
    "JPM": "jpmorgan-chase", "BAC": "bank-of-america", "WFC": "wells-fargo",
    "GS": "goldman-sachs-group", "MS": "morgan-stanley", "C": "citigroup",
    "V": "visa", "MA": "mastercard", "PYPL": "paypal-holdings",
    "DIS": "walt-disney", "CMCSA": "comcast", "T": "att",
    "JNJ": "johnson-and-johnson", "PFE": "pfizer", "UNH": "unitedhealth-group",
    "MRK": "merck", "ABBV": "abbvie", "LLY": "eli-lilly-and-company",
    "KO": "coca-cola", "PEP": "pepsico", "MCD": "mcdonalds",
    "WMT": "walmart", "COST": "costco-wholesale", "HD": "home-depot",
    "NKE": "nike", "SBUX": "starbucks", "TGT": "target",
    "BA": "boeing", "CAT": "caterpillar", "GE": "ge-aerospace",
    "XOM": "exxon-mobil", "CVX": "chevron", "COP": "conocophillips",
    "PLTR": "palantir-technologies", "SNOW": "snowflake", "UBER": "uber-technologies",
    "SQ": "block", "SHOP": "shopify", "SPOT": "spotify-technology",
    "COIN": "coinbase-global", "RIVN": "rivian-automotive", "LCID": "lucid-group",
    "GME": "gamestop", "AMC": "amc-entertainment-holdings", "SOFI": "sofi-technologies",
}

# ── Gemini 설정 ──
_model = None

def _get_model():
    global _model
    if _model is None and GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            _model = genai.GenerativeModel('gemini-2.5-flash-lite')
            logger.info("Gemini model initialized (gemini-2.5-flash-lite)")
        except Exception as e:
            logger.error(f"Gemini init failed: {e}")
    return _model


def is_available():
    return bool(GOOGLE_API_KEY)


# ── Motley Fool 어닝콜 트랜스크립트 ──

_MF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _get_company_slug(ticker: str, company_name: str = "") -> str:
    """종목 티커로 Motley Fool URL용 회사명 슬러그 생성"""
    # 매핑 테이블에 있으면 사용
    slug = _COMPANY_SLUGS.get(ticker.upper())
    if slug:
        return slug
    # 없으면 회사명에서 생성
    if company_name:
        slug = company_name.lower()
        # 접미사 제거
        for suffix in [", inc.", ", inc", " inc.", " inc", " corp.", " corp",
                       " corporation", " co.", " ltd.", " ltd", " llc",
                       " plc", " n.v.", " s.a.", " se", " ag"]:
            slug = slug.replace(suffix, "")
        slug = re.sub(r'[^a-z0-9\s-]', '', slug).strip()
        slug = re.sub(r'\s+', '-', slug)
        return slug
    return ticker.lower()


def _get_slug_variations(ticker: str, company_name: str = "") -> list[str]:
    """Motley Fool URL용 가능한 슬러그 변형 목록 반환.

    예: "Crocs, Inc." → ["crocs", "crocs-inc", "crox"] (여러 변형 시도)
    """
    variations = []
    primary = _get_company_slug(ticker, company_name)
    variations.append(primary)

    # 티커 자체도 시도 (매핑 테이블이 아닌 경우)
    ticker_slug = ticker.lower()
    if ticker_slug != primary and ticker_slug not in variations:
        variations.append(ticker_slug)

    if company_name:
        name_lower = company_name.lower()

        # 1. 회사명 첫 단어만 (예: "Crocs, Inc." → "crocs")
        first_word = re.split(r'[\s,.\-]+', name_lower)[0]
        if first_word and first_word not in variations:
            variations.append(first_word)

        # 2. 전체 이름 (접미사 포함, 예: "crocs-inc")
        full_slug = re.sub(r'[^a-z0-9\s-]', '', name_lower).strip()
        full_slug = re.sub(r'\s+', '-', full_slug)
        if full_slug and full_slug not in variations:
            variations.append(full_slug)

        # 3. "The" 제거 (예: "The Walt Disney Company" → "walt-disney-company")
        if name_lower.startswith("the "):
            no_the = name_lower[4:]
            for suffix in [" company", " corporation", " corp", " inc", " ltd", " group"]:
                no_the = no_the.replace(suffix, "")
            no_the = re.sub(r'[^a-z0-9\s-]', '', no_the).strip()
            no_the = re.sub(r'\s+', '-', no_the)
            if no_the and no_the not in variations:
                variations.append(no_the)

        # 4. "-holdings", "-technologies", "-group" 없는 버전
        for suffix in ["-holdings", "-technologies", "-group", "-company",
                       "-corporation", "-inc", "-ltd", "-entertainment",
                       "-automotive", "-platforms"]:
            stripped = primary.replace(suffix, "").rstrip("-")
            if stripped and stripped != primary and stripped not in variations:
                variations.append(stripped)

    return variations


# ── 성공한 슬러그 캐시 (메모리) ──
# {ticker: slug} — 한 분기에서 성공한 슬러그를 다른 분기에 재사용
_successful_slugs: dict[str, str] = {}


async def _load_successful_slug(ticker: str) -> str | None:
    """DB에서 이전에 성공한 트랜스크립트 URL의 슬러그 패턴 추출"""
    if ticker in _successful_slugs:
        return _successful_slugs[ticker]
    try:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT filing_url FROM guidance_analysis WHERE ticker=? AND source_type='transcript' LIMIT 1",
                (ticker,)
            )
            row = await cursor.fetchone()
            if row and row[0] and row[0].startswith("https://www.fool.com/"):
                url = row[0]
                # URL에서 슬러그 추출: .../{slug}-{ticker}-q{Q}-{YYYY}-...
                match = re.search(r'/([a-z0-9-]+)-' + ticker.lower() + r'-q\d', url)
                if match:
                    slug = match.group(1)
                    _successful_slugs[ticker] = slug
                    return slug
                # 티커 없는 패턴: .../{slug}-q{Q}-{YYYY}-...
                match = re.search(r'/([a-z0-9-]+)-q\d+-\d{4}-earnings', url)
                if match:
                    slug = match.group(1)
                    _successful_slugs[ticker] = slug
                    return slug
    except Exception:
        pass
    return None


def _guess_fiscal_quarters(report_date: str) -> list[tuple[int, int]]:
    """report_date로부터 가능한 (fiscal_quarter, fiscal_year) 후보 추정.

    회사마다 회계연도가 다르므로, report_date(어닝 발표일) 월을 기반으로
    가능한 분기 조합을 여러 개 반환한다.
    Returns: [(quarter, year), ...] 시도할 순서대로
    """
    try:
        rd = datetime.strptime(report_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return []

    month = rd.month
    year = rd.year

    # 발표일 월 → 가능한 (Q, Year) 매핑
    # 1월: Q4/이전년 또는 Q1/올해 (Apple=Q1, 대부분=Q4)
    # 2월: Q4/이전년 또는 Q1/올해
    # 4월: Q1/올해 또는 Q2/올해 (Apple=Q2)
    # 5월: Q1/올해 또는 Q2/올해
    # 7월: Q2/올해 또는 Q3/올해 (Apple=Q3)
    # 8월: Q2/올해 또는 Q3/올해
    # 10월: Q3/올해 또는 Q4/올해 (Apple=Q4)
    # 11월: Q3/올해 또는 Q4/올해
    candidates = {
        1:  [(4, year - 1), (1, year)],
        2:  [(4, year - 1), (1, year)],
        3:  [(4, year - 1), (1, year)],
        4:  [(1, year), (2, year)],
        5:  [(1, year), (2, year)],
        6:  [(2, year), (1, year)],
        7:  [(2, year), (3, year)],
        8:  [(2, year), (3, year)],
        9:  [(3, year)],
        10: [(3, year), (4, year)],
        11: [(3, year), (4, year)],
        12: [(4, year), (3, year)],
    }

    return candidates.get(month, [(1, year)])


def _extract_transcript_text(html: str) -> str | None:
    """Motley Fool 페이지 HTML에서 트랜스크립트 텍스트 추출"""
    if "transcript-content" not in html:
        return None

    match = re.search(
        r'class="article-body transcript-content"[^>]*>(.*)',
        html, re.DOTALL
    )
    if not match:
        return None

    content = match.group(1)[:80000]

    # HTML → 텍스트
    clean = re.sub(r'<[^>]+>', '\n', content)
    clean = re.sub(r'&nbsp;', ' ', clean)
    clean = re.sub(r'&#x27;', "'", clean)
    clean = re.sub(r'&#\d+;', ' ', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\n+', '\n', clean).strip()

    if len(clean) < 1000:
        return None
    return clean


def _try_fetch_url(url: str) -> tuple[str | None, str | None]:
    """URL에서 트랜스크립트 텍스트 추출. 성공 시 (text, url) 반환."""
    try:
        resp = requests.get(url, headers=_MF_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None, None
        text = _extract_transcript_text(resp.text)
        if text:
            return text, url
        return None, None
    except Exception:
        return None, None


# ── Motley Fool 사이트맵 캐시 (메모리) ──
# {(year, month): {ticker_lower: [url, ...]}} — 한 번 로드하면 재사용
_sitemap_cache: dict[tuple[int, int], dict[str, list[str]]] = {}


def _load_sitemap_month(year: int, month: int) -> dict[str, list[str]]:
    """Motley Fool 사이트맵에서 해당 월의 트랜스크립트 URL 맵 로드.

    Returns: {ticker_lower: [url1, url2, ...]}
    """
    key = (year, month)
    if key in _sitemap_cache:
        return _sitemap_cache[key]

    url = f"https://www.fool.com/sitemap/{year}/{month:02d}"
    try:
        resp = requests.get(url, headers=_MF_HEADERS, timeout=15)
        if resp.status_code != 200:
            _sitemap_cache[key] = {}
            return {}

        # XML에서 트랜스크립트 URL만 추출
        transcript_urls = re.findall(
            r'<loc>(https://www\.fool\.com/earnings/call-transcripts/[^<]+)</loc>',
            resp.text
        )

        # 티커별로 그룹핑 (URL에서 티커 추출)
        ticker_map: dict[str, list[str]] = {}
        for t_url in transcript_urls:
            # URL 패턴: .../{slug}-{TICKER}-q{Q}-{YYYY}-earnings-call-transcript/
            # 또는: .../{slug}-{TICKER}-{TICKER}-q{Q}-... (드물게)
            # 티커는 보통 대문자 → URL에서는 소문자
            # 파일명 부분만 추출
            path_part = t_url.rsplit("/", 2)[-2] if t_url.endswith("/") else t_url.rsplit("/", 1)[-1]
            # earnings-call-transcript 앞 부분에서 티커 추출
            # 패턴: {slug}-{ticker}-q{Q}-{year}-earnings-call-transcript
            match = re.search(r'-([a-z]{1,6})-q\d+-\d{4}-earnings-call', path_part)
            if match:
                t = match.group(1)
                if t not in ticker_map:
                    ticker_map[t] = []
                ticker_map[t].append(t_url)

        logger.info(f"Sitemap {year}/{month:02d}: {len(transcript_urls)} transcripts, {len(ticker_map)} tickers")
        _sitemap_cache[key] = ticker_map
        return ticker_map

    except Exception as e:
        logger.debug(f"Sitemap load failed for {year}/{month:02d}: {e}")
        _sitemap_cache[key] = {}
        return {}


def _search_sitemap_transcript(ticker: str, report_date: str,
                                quarter: int = 0, year: int = 0) -> str | None:
    """Motley Fool 사이트맵에서 트랜스크립트 URL 검색.

    report_date 기준 해당 월 ± 1개월 사이트맵을 검색.
    Returns: 매칭되는 transcript URL 또는 None
    """
    try:
        rd = datetime.strptime(report_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    ticker_lower = ticker.lower()

    # 해당 월 ± 1개월 사이트맵 검색
    months_to_check = []
    for offset in [0, -1, 1]:
        m = rd.month + offset
        y = rd.year
        if m < 1:
            m += 12
            y -= 1
        elif m > 12:
            m -= 12
            y += 1
        months_to_check.append((y, m))

    for y, m in months_to_check:
        ticker_map = _load_sitemap_month(y, m)
        urls = ticker_map.get(ticker_lower, [])

        if not urls:
            continue

        # 분기/연도가 맞는 URL 우선
        if quarter and year:
            for url in urls:
                if f"q{quarter}-{year}" in url:
                    # 사이트맵 URL이 잘려있을 수 있음 — 완전한 URL로 복원
                    if not url.endswith("earnings-call-transcript/"):
                        url = re.sub(r'earnings-call.*$', 'earnings-call-transcript/', url)
                    logger.info(f"Sitemap found exact match: {url}")
                    return url

        # 분기 매칭 안 되면 첫 번째 URL 반환 (해당 월에 하나만 있을 가능성 높음)
        if len(urls) == 1:
            logger.info(f"Sitemap found single match: {urls[0]}")
            return urls[0]

        # 여러 개면 가장 가까운 날짜 선택
        best_url = None
        best_gap = 999
        for url in urls:
            date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if date_match:
                try:
                    url_date = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                    gap = abs((rd - url_date).days)
                    if gap < best_gap:
                        best_gap = gap
                        best_url = url
                except ValueError:
                    pass

        if best_url:
            logger.info(f"Sitemap found closest match ({best_gap}d gap): {best_url}")
            return best_url

    return None


def _fetch_earnings_transcript(ticker: str, report_date: str,
                                fiscal_quarter: int = 0, fiscal_year: int = 0,
                                company_name: str = "") -> tuple[str | None, str | None]:
    """Motley Fool에서 어닝콜 트랜스크립트 텍스트를 가져온다.

    3단계 전략:
    1단계: 캐시된 성공 슬러그 + URL 추측 (빠름)
    2단계: 다양한 슬러그 변형으로 URL 추측 (중간)
    3단계: DuckDuckGo 검색으로 정확한 URL 발견 (느리지만 정확)

    Returns: (transcript_text, source_url) 또는 (None, None)
    """
    from datetime import timedelta

    ticker_lower = ticker.lower()
    slug_variations = _get_slug_variations(ticker, company_name)

    # 캐시된 성공 슬러그가 있으면 최우선으로 시도
    cached_slug = _successful_slugs.get(ticker.upper())
    if cached_slug and cached_slug not in slug_variations:
        slug_variations.insert(0, cached_slug)

    try:
        rd = datetime.strptime(report_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None, None

    # 가능한 (Q, Year) 후보
    quarter_candidates = []
    if fiscal_quarter and fiscal_year:
        quarter_candidates.append((fiscal_quarter, fiscal_year))
    guessed = _guess_fiscal_quarters(report_date)
    for g in guessed:
        if g not in quarter_candidates:
            quarter_candidates.append(g)

    if not quarter_candidates:
        return None, None

    # ── 1단계: 가장 유력한 슬러그 + 정확한 날짜 (최소 시도) ──
    primary_slug = slug_variations[0]
    seen = set()
    for fq, fy in quarter_candidates[:2]:  # 최대 2개 분기 후보
        date_part = rd.strftime("%Y/%m/%d")
        url = (f"https://www.fool.com/earnings/call-transcripts/{date_part}/"
               f"{primary_slug}-{ticker_lower}-q{fq}-{fy}-earnings-call-transcript/")
        seen.add(url)
        text, found_url = _try_fetch_url(url)
        if text:
            _cache_successful_slug(ticker, url)
            logger.info(f"{ticker}: Transcript fetched (quick) ({len(text)} chars)")
            return text, found_url

    # ── 2단계: 사이트맵 검색 (1 HTTP 요청으로 정확한 URL 발견) ──
    for fq, fy in quarter_candidates[:2]:
        sitemap_url = _search_sitemap_transcript(ticker, report_date, fq, fy)
        if sitemap_url:
            text, found_url = _try_fetch_url(sitemap_url)
            if text:
                _cache_successful_slug(ticker, sitemap_url)
                logger.info(f"{ticker}: Transcript found via sitemap ({len(text)} chars)")
                return text, found_url

    # ── 3단계: 다양한 슬러그 변형 + 넓은 날짜 범위 (최후 폴백) ──
    for slug in slug_variations[1:]:  # 이미 시도한 primary_slug 제외
        for fq, fy in quarter_candidates:
            for day_offset in range(0, 4):  # 0 ~ ±3
                for sign in [0, 1, -1]:
                    if day_offset == 0 and sign != 0:
                        continue
                    d = rd + timedelta(days=sign * day_offset)
                    date_part = d.strftime("%Y/%m/%d")
                    for pattern in [
                        f"{slug}-{ticker_lower}-q{fq}-{fy}-earnings-call-transcript/",
                        f"{slug}-q{fq}-{fy}-earnings-call-transcript/",
                    ]:
                        url = f"https://www.fool.com/earnings/call-transcripts/{date_part}/{pattern}"
                        if url in seen:
                            continue
                        seen.add(url)
                        text, found_url = _try_fetch_url(url)
                        if text:
                            _cache_successful_slug(ticker, url)
                            logger.info(f"{ticker}: Transcript fetched (fallback) ({len(text)} chars)")
                            return text, found_url

    logger.debug(f"{ticker}: No transcript found for report_date={report_date}")
    return None, None


def _cache_successful_slug(ticker: str, url: str):
    """성공한 URL에서 슬러그를 추출하여 메모리 캐시에 저장"""
    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()
    # URL에서 슬러그 추출: .../{slug}-{ticker}-q{Q}-...
    match = re.search(r'/([a-z0-9-]+)-' + re.escape(ticker_lower) + r'-q\d', url)
    if match:
        _successful_slugs[ticker_upper] = match.group(1)
        return
    # 티커 없는 패턴: .../{slug}-q{Q}-...
    match = re.search(r'/([a-z0-9-]+)-q\d+-\d{4}-earnings', url)
    if match:
        _successful_slugs[ticker_upper] = match.group(1)


def _parse_fiscal_quarter(period_end: str) -> tuple[int, int]:
    """period_end (YYYY-MM-DD) → (fiscal_quarter, fiscal_year) 추정.
    대부분의 미국 기업은 달력 분기를 따르지만, Apple 등은 다름.
    SEC 데이터의 period를 사용하는 게 더 정확하지만 없을 때 추정용.
    """
    try:
        d = datetime.strptime(period_end, "%Y-%m-%d")
        month = d.month
        year = d.year
        # 일반적 달력 분기
        if month <= 3:
            return 1, year
        elif month <= 6:
            return 2, year
        elif month <= 9:
            return 3, year
        else:
            return 4, year
    except (ValueError, TypeError):
        return 0, 0


# ── SEC EDGAR 8-K 텍스트 가져오기 ──

SEC_HEADERS = {
    "User-Agent": "FinVision admin@finvision.app",
    "Accept-Encoding": "gzip, deflate",
}


def _get_8k_filings(cik: str, limit: int = 25) -> list:
    """SEC EDGAR에서 8-K 공시 목록 가져오기 (Exhibit 포함)"""
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        cik_num = cik.lstrip("0")
        filings = []
        for i, form in enumerate(forms):
            if form in ("8-K", "8-K/A") and i < len(dates) and i < len(accessions):
                acc_no = accessions[i].replace("-", "")
                base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_no}"
                primary_url = f"{base_url}/{primary_docs[i]}" if i < len(primary_docs) else ""

                # Exhibit (어닝 프레스 릴리스) URL을 찾기 위해 인덱스 페이지 탐색
                exhibit_url = _find_exhibit_url(base_url)

                filings.append({
                    "form": form,
                    "date": dates[i],
                    "accession": accessions[i],
                    "url": exhibit_url or primary_url,
                    "primary_url": primary_url,
                })
                if len(filings) >= limit:
                    break

        return filings
    except Exception as e:
        logger.warning(f"SEC 8-K list fetch failed: {e}")
        return []


def _find_exhibit_url(base_url: str) -> str | None:
    """8-K 인덱스 페이지에서 Exhibit 99.1 (어닝 프레스 릴리스) URL 찾기"""
    try:
        resp = requests.get(base_url + "/", headers=SEC_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None

        # exhibit99 패턴 찾기 (exhibit991.htm, ex991.htm, exhibit99-1.htm 등)
        patterns = [
            r'href="([^"]*exhibit\s*99[^"]*\.htm[l]?)"',
            r'href="([^"]*ex99[^"]*\.htm[l]?)"',
            r'href="([^"]*ex-99[^"]*\.htm[l]?)"',
            r'href="([^"]*press[^"]*\.htm[l]?)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            for match in matches:
                # 상대 경로를 절대 경로로 변환
                if match.startswith("http"):
                    return match
                elif match.startswith("/"):
                    return f"https://www.sec.gov{match}"
                else:
                    return f"{base_url}/{match}"

        return None
    except Exception:
        return None


def _download_filing_text(url: str, max_chars: int = 15000) -> str:
    """8-K 공시 텍스트 다운로드 (HTML → 텍스트 변환, 최대 글자수 제한)"""
    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=20)
        resp.raise_for_status()
        text = resp.text

        # HTML 태그 제거
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # 토큰 절약: 최대 글자수 제한
        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"

        return text
    except Exception as e:
        logger.warning(f"Filing download failed ({url}): {e}")
        return ""


def _match_filing_to_earnings(filings: list, earnings_dates: list) -> dict:
    """8-K 공시를 어닝 발표일과 매칭 (±7일 tolerance)

    Returns: {period_end: filing_info}
    """
    matched = {}
    for ed in earnings_dates:
        report_date = ed.get("report_date") or ed.get("date")
        period_end = ed.get("period_end")
        if not report_date or not period_end:
            continue

        try:
            rd = datetime.strptime(report_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        best_filing = None
        best_gap = 999

        for f in filings:
            try:
                fd = datetime.strptime(f["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            gap = abs((rd - fd).days)
            if gap <= 7 and gap < best_gap:
                best_gap = gap
                best_filing = f

        if best_filing:
            matched[period_end] = best_filing

    return matched


# ── Gemini 분석 프롬프트 ──

TRANSCRIPT_PROMPT = """당신은 월가 20년 경력의 시니어 이퀴티 리서치 애널리스트입니다.
Goldman Sachs와 Morgan Stanley에서 섹터 리드 애널리스트를 역임했으며,
수천 건의 어닝콜과 8-K 공시를 분석한 전문가입니다.

아래는 {ticker}의 {period} 분기 어닝콜 트랜스크립트 (CEO/CFO 발언 + 애널리스트 Q&A 포함)입니다.

이 어닝콜을 분석하여 아래 JSON 형식으로 결과를 반환하세요.
반드시 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요.

핵심 분석 포인트:
- CEO/CFO가 다음 분기 또는 연간 전망에 대해 한 발언 (가이던스)
- 애널리스트 Q&A에서 나온 우려 사항과 경영진 답변
- 언급된 구체적 수치 (매출 목표, 마진 목표, 생산량, 투자 규모 등)
- 시장이 가장 주목했을 포인트

{{
  "guidance_summary": "가이던스 핵심 내용 2-3문장 요약 (한국어). CEO/CFO가 제시한 다음 분기/연간 전망 중심으로",
  "key_themes": ["핵심 테마 태그 3-5개 (한국어, 예: 마진압박, AI투자확대, 가격인하, 수요둔화, 신제품출시)"],
  "sentiment_score": 0-100 사이 정수 (50=중립, 0=매우부정, 100=매우긍정),
  "revenue_guidance": "매출 가이던스 요약 (CEO/CFO가 언급한 수치 포함, 없으면 '미제시')",
  "margin_guidance": "마진/수익성 가이던스 요약 (수치 포함, 없으면 '미제시')",
  "specific_numbers": "언급된 구체적 수치/목표 (배달량, 생산량, 투자규모, 구독자 수 등)",
  "ai_annotation": "이 어닝콜에서 시장이 주목했을 핵심 포인트 1-2문장 (한국어). 주가가 왜 올랐/떨어졌을지 추론",
  "impact_factor": "주가 변동의 주요 원인 추정 (guidance/eps/revenue/macro/sentiment 중 택1)"
}}

=== 어닝콜 트랜스크립트 ===
{filing_text}
"""

FILING_PROMPT = """당신은 월가 20년 경력의 시니어 이퀴티 리서치 애널리스트입니다.
Goldman Sachs와 Morgan Stanley에서 섹터 리드 애널리스트를 역임했으며,
수천 건의 어닝콜과 8-K 공시를 분석한 전문가입니다.

아래는 {ticker}의 {period} 분기 실적 발표 8-K 공시 원문입니다.
(어닝콜 트랜스크립트가 없어 프레스 릴리스를 분석합니다)

이 공시를 분석하여 아래 JSON 형식으로 결과를 반환하세요.
반드시 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요.

{{
  "guidance_summary": "가이던스 핵심 내용 2-3문장 요약 (한국어)",
  "key_themes": ["핵심 테마 태그 3-5개 (한국어, 예: 마진압박, AI투자확대, 가격인하)"],
  "sentiment_score": 0-100 사이 정수 (50=중립, 0=매우부정, 100=매우긍정),
  "revenue_guidance": "매출 가이던스 요약 (수치 포함, 없으면 '미제시')",
  "margin_guidance": "마진/수익성 가이던스 요약 (수치 포함, 없으면 '미제시')",
  "specific_numbers": "언급된 구체적 수치/목표 (배달량, 생산량, 투자규모 등)",
  "ai_annotation": "이 분기 실적에서 시장이 주목했을 핵심 포인트 1-2문장 (한국어). 주가가 왜 올랐/떨어졌을지 추론",
  "impact_factor": "주가 변동의 주요 원인 추정 (guidance/eps/revenue/macro/sentiment 중 택1)"
}}

=== 8-K 공시 원문 ===
{filing_text}
"""


def _analyze_with_gemini(ticker: str, period: str, filing_text: str,
                         source_type: str = "filing") -> dict | None:
    """Gemini로 텍스트 분석

    Args:
        source_type: "transcript" (어닝콜) or "filing" (8-K 프레스 릴리스)
    """
    model = _get_model()
    if not model:
        return None

    if len(filing_text.strip()) < 200:
        logger.warning(f"Text too short for {ticker} {period}")
        return None

    # 트랜스크립트는 길 수 있으므로 Gemini 토큰 제한 고려 (약 25000자)
    max_chars = 30000 if source_type == "transcript" else 15000
    if len(filing_text) > max_chars:
        filing_text = filing_text[:max_chars] + "\n... [truncated]"

    template = TRANSCRIPT_PROMPT if source_type == "transcript" else FILING_PROMPT
    prompt = template.format(
        ticker=ticker,
        period=period,
        filing_text=filing_text
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # JSON 추출 (마크다운 코드블록 제거)
        if text.startswith("```"):
            text = re.sub(r'^```(?:json)?\n?', '', text)
            text = re.sub(r'\n?```$', '', text)

        result = json.loads(text)
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"Gemini JSON parse error for {ticker} {period}: {e}")
        # 부분 텍스트라도 저장
        return {"guidance_summary": text[:500], "parse_error": True}
    except Exception as e:
        logger.error(f"Gemini analysis failed for {ticker} {period}: {e}")
        return None


# ── DB 캐시 관리 ──

async def _get_cached_guidance(ticker: str) -> list:
    """DB에서 캐싱된 가이던스 분석 가져오기"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM guidance_analysis WHERE ticker=? ORDER BY period_end DESC",
            (ticker,)
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # JSON 필드 파싱
            if d.get("key_themes"):
                try:
                    d["key_themes"] = json.loads(d["key_themes"])
                except (json.JSONDecodeError, TypeError):
                    d["key_themes"] = []
            else:
                d["key_themes"] = []
            results.append(d)
        return results


async def _save_guidance(ticker: str, period_end: str, report_date: str,
                         filing_url: str, analysis: dict, source_type: str = "filing"):
    """가이던스 분석 결과 DB에 저장"""
    async with aiosqlite.connect(DB_PATH) as db:
        # source_type 컬럼이 없으면 추가
        try:
            await db.execute("ALTER TABLE guidance_analysis ADD COLUMN source_type TEXT DEFAULT 'filing'")
            await db.commit()
        except Exception:
            pass  # 이미 존재

        themes_json = json.dumps(analysis.get("key_themes", []), ensure_ascii=False)

        # Gemini가 리스트/딕트를 반환할 수 있으므로 모든 텍스트 필드를 문자열로 변환
        def _str(val):
            if isinstance(val, (list, dict)):
                return json.dumps(val, ensure_ascii=False)
            return str(val) if val is not None else ""

        await db.execute("""
            INSERT OR REPLACE INTO guidance_analysis
            (ticker, period_end, report_date, filing_url, guidance_summary,
             key_themes, sentiment_score, revenue_guidance, margin_guidance,
             specific_numbers, ai_annotation, impact_factor, raw_response, analyzed_at,
             source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, period_end, report_date, filing_url,
            _str(analysis.get("guidance_summary", "")),
            themes_json,
            analysis.get("sentiment_score"),
            _str(analysis.get("revenue_guidance", "")),
            _str(analysis.get("margin_guidance", "")),
            _str(analysis.get("specific_numbers", "")),
            _str(analysis.get("ai_annotation", "")),
            _str(analysis.get("impact_factor", "")),
            json.dumps(analysis, ensure_ascii=False),
            datetime.now().isoformat(),
            source_type,
        ))
        await db.commit()


# ── 동시 분석 방지 락 (종목별) ──
# 같은 종목에 대해 여러 요청이 동시에 들어와도
# 첫 번째 요청만 Gemini를 호출하고, 나머지는 결과를 기다림
_analysis_locks: dict[str, asyncio.Lock] = {}
_analysis_futures: dict[str, asyncio.Task] = {}


def _get_lock(ticker: str) -> asyncio.Lock:
    """종목별 asyncio Lock 반환 (없으면 생성)"""
    if ticker not in _analysis_locks:
        _analysis_locks[ticker] = asyncio.Lock()
    return _analysis_locks[ticker]


# ── 메인 분석 함수 ──

async def analyze_guidance_for_stock(ticker: str, cik: str, earnings_history: list,
                                     max_quarters: int = 20,
                                     company_name: str = "") -> list:
    """종목의 가이던스를 분석하여 반환.
    이미 캐싱된 분기는 건너뛰고, 새로운 분기만 Gemini로 분석.
    동시 요청 시 종목별 Lock으로 중복 Gemini 호출 방지.

    Args:
        ticker: 종목 티커
        cik: SEC CIK (10자리 zero-padded)
        earnings_history: 어닝 히스토리 [{period_end, report_date, date, period, ...}]
        max_quarters: 최대 분석 분기 수 (비용 제어)
        company_name: 회사명 (Motley Fool URL 생성용)

    Returns: list of guidance analysis dicts
    """
    if not is_available():
        return []

    lock = _get_lock(ticker)

    # 락 획득 시도 — 이미 다른 요청이 분석 중이면 캐시만 반환
    if lock.locked():
        logger.info(f"{ticker}: Another request is already analyzing, returning cached data")
        return await _get_cached_guidance(ticker)

    async with lock:
        return await _analyze_guidance_locked(ticker, cik, earnings_history, max_quarters, company_name)


async def _analyze_guidance_locked(ticker: str, cik: str, earnings_history: list,
                                    max_quarters: int, company_name: str = "") -> list:
    """실제 분석 로직 (Lock 내부에서 실행)

    1순위: Motley Fool 어닝콜 트랜스크립트 → Gemini 분석
    2순위: SEC 8-K 프레스 릴리스 → Gemini 분석 (폴백)
    이미 캐싱된 분기는 건너뜀.
    """
    # 1. 캐싱된 결과 가져오기
    cached = await _get_cached_guidance(ticker)
    cached_periods = {c["period_end"] for c in cached}

    # 2. 분석 필요한 분기 파악 (최근 max_quarters개) — 캐시에 없는 것만
    recent_history = sorted(earnings_history, key=lambda x: x.get("period_end", ""), reverse=True)[:max_quarters]
    need_analysis = [h for h in recent_history
                     if h.get("period_end") and h["period_end"] not in cached_periods]

    if not need_analysis:
        logger.info(f"{ticker}: All {len(cached)} quarters already cached")
        return cached

    # 3. 8-K 공시 목록 (트랜스크립트 실패 시 폴백용 — 필요할 때 로드)
    # 4. 새로운 분기 분석
    new_count = 0
    filings = None
    matched = None

    for h in need_analysis:
        pe = h.get("period_end")
        if not pe:
            continue

        period = h.get("period", pe)
        report_date = h.get("report_date") or h.get("date") or pe

        # ── 1순위: Motley Fool 어닝콜 트랜스크립트 ──
        # period_end에서 분기/연도를 직접 추출 (회계연도 추정보다 정확)
        fq, fy = _parse_fiscal_quarter(pe)

        # 이전에 성공한 슬러그 로드 (첫 분기에만)
        if new_count == 0 and not _successful_slugs.get(ticker):
            cached_slug = await _load_successful_slug(ticker)
            if cached_slug:
                logger.info(f"{ticker}: Loaded cached slug: {cached_slug}")

        transcript, transcript_url = await asyncio.to_thread(
            _fetch_earnings_transcript, ticker, report_date,
            fiscal_quarter=fq, fiscal_year=fy,
            company_name=company_name
        )

        if transcript:
            # 트랜스크립트를 Gemini로 분석
            analysis = await asyncio.to_thread(
                _analyze_with_gemini, ticker, period, transcript, "transcript"
            )
            if analysis:
                source_url = transcript_url or f"motley-fool:transcript:{ticker}:{period}"
                await _save_guidance(ticker, pe, report_date, source_url, analysis, "transcript")
                new_count += 1
                logger.info(f"{ticker} {period}: Transcript analyzed (sentiment={analysis.get('sentiment_score')})")
                continue

        # 트랜스크립트를 찾지 못한 분기는 건너뜀 (사용자 요구: 무조건 transcript만 분석)
        logger.warning(f"{ticker} {period}: No transcript available — skipped")

    if new_count > 0:
        logger.info(f"{ticker}: {new_count} new quarters analyzed with Gemini")

    # 5. 전체 결과 반환 (캐시 + 새로 분석된 것)
    return await _get_cached_guidance(ticker)


# ── 테마 기반 패턴 매칭 ──

def compute_theme_patterns(guidance_list: list, earnings_history: list) -> dict:
    """과거 가이던스 테마별 주가 반응 패턴 계산.

    Returns: {
        "themes": {
            "마진압박": {"count": 5, "avg_reaction": -3.2, "cases": [...]},
            ...
        },
        "all_themes": ["마진압박", "AI투자확대", ...],
    }
    """
    # earnings_history를 period_end로 인덱싱
    reaction_map = {}
    for h in earnings_history:
        pe = h.get("period_end")
        if pe and h.get("reaction_1d_change") is not None:
            reaction_map[pe] = h["reaction_1d_change"]

    theme_data = {}
    all_themes = set()

    for g in guidance_list:
        pe = g.get("period_end")
        themes = g.get("key_themes", [])
        reaction = reaction_map.get(pe)

        if not themes or reaction is None:
            continue

        for theme in themes:
            theme = theme.strip()
            if not theme:
                continue
            all_themes.add(theme)

            if theme not in theme_data:
                theme_data[theme] = {"reactions": [], "cases": []}

            theme_data[theme]["reactions"].append(reaction)
            theme_data[theme]["cases"].append({
                "period_end": pe,
                "period": g.get("report_date", pe),
                "reaction": reaction,
                "sentiment": g.get("sentiment_score"),
                "summary": g.get("guidance_summary", "")[:100],
            })

    # 통계 계산
    themes_result = {}
    for theme, data in theme_data.items():
        reactions = data["reactions"]
        if len(reactions) >= 1:
            themes_result[theme] = {
                "count": len(reactions),
                "avg_reaction": round(sum(reactions) / len(reactions), 2),
                "min_reaction": round(min(reactions), 2),
                "max_reaction": round(max(reactions), 2),
                "up_pct": round(sum(1 for r in reactions if r > 0) / len(reactions) * 100, 1),
                "cases": sorted(data["cases"], key=lambda x: x.get("period_end", ""), reverse=True)[:5],
            }

    return {
        "themes": dict(sorted(themes_result.items(), key=lambda x: x[1]["count"], reverse=True)),
        "all_themes": sorted(all_themes),
    }
