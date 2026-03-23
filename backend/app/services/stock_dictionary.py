"""
한국어/영어 종목명 사전 + 퍼지 검색

- 한국어 이름으로 검색 가능 (아마존 → AMZN)
- 오타 허용 (amazin, anmazon, 아마쥰 → AMZN)
- 대소문자 무시
- 부분 일치 지원
"""

import difflib
import re

# ── 한국어 초성 (Korean initial consonants) ─────────────────────────
CHOSUNG = [
    'ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ',
    'ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ',
]
_JAMO_CONSONANTS = set(CHOSUNG)

def get_chosung(text: str) -> str:
    """한국어 텍스트에서 초성만 추출 (비한글 문자는 그대로 유지)"""
    result = ''
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:  # 완성형 한글 음절
            cho_idx = (code - 0xAC00) // 588
            result += CHOSUNG[cho_idx]
        else:
            result += ch
    return result

def _is_all_chosung(text: str) -> bool:
    """텍스트가 모두 한국어 초성 자음인지 확인"""
    return len(text) > 0 and all(ch in _JAMO_CONSONANTS for ch in text)

# ── 주요 미국 주식 사전 ──────────────────────────────────────────
# (ticker, 영문명, 한국어명들, 한국어 별명들)
STOCK_DB = [
    # 빅테크
    ("AAPL",  "Apple Inc.",                    ["애플"]),
    ("MSFT",  "Microsoft Corporation",         ["마이크로소프트", "마소", "MS"]),
    ("GOOGL", "Alphabet Inc.",                 ["구글", "알파벳", "Google"]),
    ("GOOG",  "Alphabet Inc. Class C",         ["구글C"]),
    ("AMZN",  "Amazon.com Inc.",               ["아마존", "Amazon"]),
    ("META",  "Meta Platforms Inc.",            ["메타", "페이스북", "Facebook"]),
    ("NVDA",  "NVIDIA Corporation",            ["엔비디아", "엔비디아", "엔브이디에이"]),
    ("TSLA",  "Tesla Inc.",                    ["테슬라"]),
    ("AVGO",  "Broadcom Inc.",                 ["브로드컴"]),
    ("TSM",   "Taiwan Semiconductor",          ["TSMC", "대만반도체", "티에스엠씨"]),

    # 반도체
    ("AMD",   "Advanced Micro Devices",        ["AMD", "에이엠디"]),
    ("INTC",  "Intel Corporation",             ["인텔"]),
    ("QCOM",  "Qualcomm Inc.",                 ["퀄컴"]),
    ("MU",    "Micron Technology",             ["마이크론"]),
    ("ARM",   "Arm Holdings",                  ["ARM", "암홀딩스"]),
    ("ASML",  "ASML Holding NV",              ["ASML", "에이에스엠엘"]),
    ("MRVL",  "Marvell Technology",            ["마벨"]),
    ("LRCX",  "Lam Research",                  ["램리서치"]),
    ("AMAT",  "Applied Materials",             ["어플라이드머티리얼즈", "어플라이드"]),
    ("KLAC",  "KLA Corporation",               ["KLA"]),
    ("ON",    "ON Semiconductor",              ["온세미컨덕터", "온세미"]),
    ("TXN",   "Texas Instruments",             ["텍사스인스트루먼트", "TI"]),

    # 소프트웨어 / 클라우드
    ("CRM",   "Salesforce Inc.",               ["세일즈포스"]),
    ("ORCL",  "Oracle Corporation",            ["오라클"]),
    ("ADBE",  "Adobe Inc.",                    ["어도비"]),
    ("NOW",   "ServiceNow Inc.",               ["서비스나우"]),
    ("SHOP",  "Shopify Inc.",                  ["쇼피파이"]),
    ("SNOW",  "Snowflake Inc.",                ["스노우플레이크"]),
    ("PLTR",  "Palantir Technologies",         ["팔란티어"]),
    ("NET",   "Cloudflare Inc.",               ["클라우드플레어"]),
    ("PANW",  "Palo Alto Networks",            ["팔로알토"]),
    ("CRWD",  "CrowdStrike Holdings",          ["크라우드스트라이크"]),
    ("DDOG",  "Datadog Inc.",                  ["데이터독"]),
    ("ZS",    "Zscaler Inc.",                  ["지스케일러"]),
    ("MDB",   "MongoDB Inc.",                  ["몽고DB"]),
    ("UBER",  "Uber Technologies",             ["우버"]),
    ("ABNB",  "Airbnb Inc.",                   ["에어비앤비"]),
    ("SQ",    "Block Inc.",                    ["블록", "스퀘어"]),
    ("COIN",  "Coinbase Global",               ["코인베이스"]),

    # AI / 로봇
    ("AI",    "C3.ai Inc.",                    ["C3AI"]),
    ("PATH",  "UiPath Inc.",                   ["유아이패스"]),
    ("IONQ",  "IonQ Inc.",                     ["아이온큐", "이온큐"]),
    ("RGTI",  "Rigetti Computing",             ["리게티"]),
    ("SMCI",  "Super Micro Computer",          ["슈퍼마이크로", "SMCI"]),

    # 전기차 / 에너지
    ("RIVN",  "Rivian Automotive",             ["리비안"]),
    ("LCID",  "Lucid Group",                   ["루시드"]),
    ("NIO",   "NIO Inc.",                      ["니오"]),
    ("XPEV",  "XPeng Inc.",                    ["샤오펑"]),
    ("LI",    "Li Auto Inc.",                  ["리오토"]),
    ("ENPH",  "Enphase Energy",                ["엔페이즈"]),
    ("FSLR",  "First Solar",                   ["퍼스트솔라"]),
    ("PLUG",  "Plug Power",                    ["플러그파워"]),

    # 금융
    ("JPM",   "JPMorgan Chase",                ["JP모건", "제이피모건"]),
    ("BAC",   "Bank of America",               ["뱅크오브아메리카", "BOA"]),
    ("GS",    "Goldman Sachs",                 ["골드만삭스"]),
    ("MS",    "Morgan Stanley",                ["모건스탠리"]),
    ("WFC",   "Wells Fargo",                   ["웰스파고"]),
    ("C",     "Citigroup Inc.",                ["시티그룹", "씨티"]),
    ("V",     "Visa Inc.",                     ["비자"]),
    ("MA",    "Mastercard Inc.",               ["마스터카드"]),
    ("PYPL",  "PayPal Holdings",               ["페이팔"]),
    ("AXP",   "American Express",              ["아메리칸익스프레스", "아멕스"]),
    ("BRK-B", "Berkshire Hathaway",            ["버크셔해서웨이", "버크셔"]),
    ("BLK",   "BlackRock Inc.",                ["블랙록"]),
    ("SCHW",  "Charles Schwab",                ["찰스슈왑"]),

    # 헬스케어 / 제약
    ("JNJ",   "Johnson & Johnson",             ["존슨앤존슨", "J&J"]),
    ("UNH",   "UnitedHealth Group",            ["유나이티드헬스"]),
    ("PFE",   "Pfizer Inc.",                   ["화이자"]),
    ("MRNA",  "Moderna Inc.",                  ["모더나"]),
    ("ABBV",  "AbbVie Inc.",                   ["애브비"]),
    ("LLY",   "Eli Lilly",                     ["일라이릴리", "릴리"]),
    ("NVO",   "Novo Nordisk",                  ["노보노디스크"]),
    ("TMO",   "Thermo Fisher Scientific",      ["써모피셔"]),
    ("ABT",   "Abbott Laboratories",           ["애보트"]),
    ("BMY",   "Bristol-Myers Squibb",          ["브리스톨마이어스"]),
    ("AMGN",  "Amgen Inc.",                    ["암젠"]),
    ("GILD",  "Gilead Sciences",               ["길리어드"]),
    ("ISRG",  "Intuitive Surgical",            ["인튜이티브서지컬", "다빈치"]),

    # 소비재 / 유통
    ("WMT",   "Walmart Inc.",                  ["월마트"]),
    ("COST",  "Costco Wholesale",              ["코스트코"]),
    ("HD",    "Home Depot",                    ["홈디포"]),
    ("TGT",   "Target Corporation",            ["타겟"]),
    ("NKE",   "Nike Inc.",                     ["나이키"]),
    ("SBUX",  "Starbucks Corporation",         ["스타벅스"]),
    ("MCD",   "McDonald's Corporation",        ["맥도날드"]),
    ("KO",    "Coca-Cola Company",             ["코카콜라"]),
    ("PEP",   "PepsiCo Inc.",                  ["펩시", "펩시코"]),
    ("PG",    "Procter & Gamble",              ["P&G", "피앤지"]),
    ("CL",    "Colgate-Palmolive",             ["콜게이트"]),

    # 통신 / 미디어
    ("DIS",   "Walt Disney Company",           ["디즈니", "월트디즈니"]),
    ("NFLX",  "Netflix Inc.",                  ["넷플릭스"]),
    ("CMCSA", "Comcast Corporation",           ["컴캐스트"]),
    ("T",     "AT&T Inc.",                     ["AT&T", "에이티앤티"]),
    ("VZ",    "Verizon Communications",        ["버라이즌"]),
    ("TMUS",  "T-Mobile US",                   ["티모바일"]),
    ("SPOT",  "Spotify Technology",            ["스포티파이"]),
    ("RBLX",  "Roblox Corporation",            ["로블록스"]),
    ("SNAP",  "Snap Inc.",                     ["스냅", "스냅챗"]),
    ("PINS",  "Pinterest Inc.",                ["핀터레스트"]),
    ("ROKU",  "Roku Inc.",                     ["로쿠"]),

    # 산업 / 방위
    ("BA",    "Boeing Company",                ["보잉"]),
    ("LMT",   "Lockheed Martin",               ["록히드마틴"]),
    ("RTX",   "RTX Corporation",               ["레이시온", "RTX"]),
    ("NOC",   "Northrop Grumman",              ["노스럽그루먼"]),
    ("GE",    "General Electric",              ["제너럴일렉트릭", "GE"]),
    ("CAT",   "Caterpillar Inc.",              ["캐터필러"]),
    ("DE",    "Deere & Company",               ["디어", "존디어"]),
    ("HON",   "Honeywell International",       ["허니웰"]),
    ("UPS",   "United Parcel Service",         ["UPS"]),
    ("FDX",   "FedEx Corporation",             ["페덱스"]),

    # 에너지
    ("XOM",   "Exxon Mobil",                   ["엑슨모빌"]),
    ("CVX",   "Chevron Corporation",           ["셰브론", "쉐브론"]),
    ("COP",   "ConocoPhillips",                ["코노코필립스"]),

    # ETF
    ("SPY",   "SPDR S&P 500 ETF Trust",        ["SPY", "S&P500", "에스앤피"]),
    ("QQQ",   "Invesco QQQ Trust",             ["큐큐큐", "나스닥100"]),
    ("IWM",   "iShares Russell 2000",          ["러셀2000"]),
    ("DIA",   "SPDR Dow Jones",                ["다우존스"]),
    ("VTI",   "Vanguard Total Stock Market",   ["뱅가드"]),
    ("ARKK",  "ARK Innovation ETF",            ["아크", "ARKK"]),
    ("SOXL",  "Direxion Semiconductor Bull",   ["SOXL", "반도체3배"]),
    ("TQQQ",  "ProShares UltraPro QQQ",        ["TQQQ", "나스닥3배"]),
    ("SQQQ",  "ProShares UltraPro Short QQQ",  ["SQQQ", "나스닥인버스3배"]),
    ("TLT",   "iShares 20+ Year Treasury",     ["장기국채", "TLT"]),
    ("GLD",   "SPDR Gold Shares",              ["금ETF", "GLD"]),
    ("SLV",   "iShares Silver Trust",          ["은ETF"]),
    ("USO",   "United States Oil Fund",        ["원유ETF"]),
    ("XLE",   "Energy Select Sector SPDR",     ["에너지ETF"]),
    ("XLF",   "Financial Select Sector SPDR",  ["금융ETF"]),
    ("XLK",   "Technology Select Sector SPDR", ["기술ETF"]),
    ("XLV",   "Health Care Select Sector SPDR",["헬스케어ETF"]),
    ("SOXX",  "iShares Semiconductor ETF",     ["반도체ETF"]),
    ("VOO",   "Vanguard S&P 500 ETF",          ["VOO"]),
    ("VGT",   "Vanguard Information Technology",["뱅가드IT"]),
    ("SCHD",  "Schwab US Dividend Equity ETF", ["SCHD", "배당ETF"]),
]

# ── 검색 인덱스 구축 ─────────────────────────────────────────────
# query_key(소문자) → [(ticker, name, source_label)]
_INDEX = {}  # 정확/부분 매칭용
_ALL_KEYS = []  # 퍼지 매칭용
_CHOSUNG_INDEX = {}  # 초성 검색용 (chosung_string → [entries])

def _normalize(s: str) -> str:
    """소문자 + 공백/특수문자 제거"""
    return re.sub(r'[^a-z0-9가-힣]', '', s.lower())

def _build_index():
    global _INDEX, _ALL_KEYS, _CHOSUNG_INDEX
    for ticker, name, kr_names in STOCK_DB:
        entry = {"ticker": ticker, "name": name}

        # 티커 자체
        key = _normalize(ticker)
        _INDEX.setdefault(key, []).append(entry)

        # 영문명
        key = _normalize(name)
        _INDEX.setdefault(key, []).append(entry)

        # 영문명 단어들 (3글자 이상만 - 짧은 단어는 노이즈 유발)
        for word in name.split():
            wkey = _normalize(word)
            if len(wkey) >= 3:
                _INDEX.setdefault(wkey, []).append(entry)

        # 한국어 이름들
        for kr in kr_names:
            key = _normalize(kr)
            _INDEX.setdefault(key, []).append(entry)

        # 초성 인덱스 추가
        for kr in kr_names:
            chosung = get_chosung(kr)
            if chosung:  # 빈 문자열이 아닌 경우에만
                _CHOSUNG_INDEX.setdefault(chosung, []).append(entry)

    _ALL_KEYS = list(_INDEX.keys())

_build_index()


# ── 검색 함수 ────────────────────────────────────────────────────

def _search_chosung(query: str, max_results: int = 8) -> list:
    """초성 검색: 초성 문자열로 종목 검색"""
    seen = set()
    results = []

    def _add(entries):
        for e in entries:
            if e["ticker"] not in seen:
                seen.add(e["ticker"])
                results.append(e)

    # 정확 초성 일치
    if query in _CHOSUNG_INDEX:
        _add(_CHOSUNG_INDEX[query])

    # 초성 prefix 일치
    if len(results) < max_results:
        for cho_key, entries in _CHOSUNG_INDEX.items():
            if cho_key.startswith(query) and cho_key != query:
                _add(entries)
            if len(results) >= max_results:
                break

    return results[:max_results]


def search_local(query: str, max_results: int = 8) -> list:
    """
    로컬 사전에서 검색. 우선순위:
    0. 초성 검색 (ㅌㅅㄹ → 테슬라)
    1. 정확 일치 (티커/이름)
    2. 시작 부분 일치
    3. 부분 문자열 포함
    4. 퍼지 매칭 (오타 허용)
    """
    raw_q = query.strip()

    # 0단계: 초성 검색 (입력이 모두 한글 자음인 경우)
    if raw_q and _is_all_chosung(raw_q):
        return _search_chosung(raw_q, max_results)

    q = _normalize(query)
    if not q:
        return []

    seen_tickers = set()
    results = []

    def _add(entries):
        for e in entries:
            if e["ticker"] not in seen_tickers:
                seen_tickers.add(e["ticker"])
                results.append(e)

    # 1단계: 정확 일치
    if q in _INDEX:
        _add(_INDEX[q])

    # 2단계: 시작 부분 일치 (prefix)
    if len(results) < max_results:
        for key in _ALL_KEYS:
            if key.startswith(q) and key != q:
                _add(_INDEX[key])
            if len(results) >= max_results:
                break

    # 3단계: 부분 문자열 포함 (substring)
    if len(results) < max_results:
        for key in _ALL_KEYS:
            if q in key and not key.startswith(q):
                _add(_INDEX[key])
            if len(results) >= max_results:
                break

    # 4단계: 퍼지 매칭 (오타 허용)
    if len(results) < max_results and len(q) >= 3:
        # cutoff을 문자열 길이에 따라 조정
        cutoff = 0.55 if len(q) >= 5 else 0.65
        close_matches = difflib.get_close_matches(q, _ALL_KEYS, n=6, cutoff=cutoff)
        for match in close_matches:
            _add(_INDEX[match])
            if len(results) >= max_results:
                break

    return results[:max_results]
