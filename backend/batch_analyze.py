"""
FinVision 배치 분석 스크립트
- S&P 500 우선 → 나머지 전체 US 종목
- 가이던스(트랜스크립트), 경쟁사, 핵심지표, 기업 소개 번역
- 이미 분석된 종목은 자동 스킵
- 로그 파일: batch_analyze.log

사용법: CMD에서
  cd finvision/backend
  python batch_analyze.py
"""

import asyncio
import hashlib
import logging
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import aiosqlite
import google.generativeai as genai

from app.services import yfinance_client
from app.services.gemini_guidance import analyze_guidance_for_stock
from app.services.stock_profile_ai import get_stock_profile
from app.services.earnings_analyzer import get_full_earnings_analysis
from app.database import DB_PATH

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('batch_analyze.log', encoding='utf-8'),
        logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)),
    ]
)
log = logging.getLogger(__name__)

# ── Gemini 설정 ──
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
translate_model = genai.GenerativeModel('gemini-2.5-flash-lite')

# ── S&P 500 종목 리스트 ──
SP500 = [
    'A','AAPL','ABBV','ABNB','ABT','ACGL','ACN','ADBE','ADI','ADM','ADP','ADSK',
    'AEE','AEP','AES','AFL','AIG','AIZ','AJG','AKAM','ALB','ALGN','ALL','ALLE',
    'AMAT','AMCR','AMD','AME','AMGN','AMP','AMT','AMZN','ANET','AON','AOS','APA',
    'APD','APH','APO','APP','APTV','ARE','ARES','ATO','AVB','AVGO','AVY','AWK',
    'AXON','AXP','AZO','BA','BAC','BALL','BAX','BBY','BDX','BEN','BF-B','BG',
    'BIIB','BK','BKNG','BKR','BLDR','BLK','BMY','BR','BRK-B','BRO','BSX','BX',
    'BXP','C','CAG','CAH','CARR','CAT','CB','CBOE','CBRE','CCI','CCL','CDNS',
    'CDW','CEG','CF','CFG','CHD','CHRW','CHTR','CI','CIEN','CINF','CL','CLX',
    'CMCSA','CME','CMG','CMI','CMS','CNC','CNP','COF','COHR','COIN','COO','COP',
    'COR','COST','CPAY','CPB','CPRT','CPT','CRH','CRL','CRM','CRWD','CSCO','CSGP',
    'CSX','CTAS','CTRA','CTSH','CTVA','CVNA','CVS','CVX','D','DAL','DASH','DD',
    'DDOG','DE','DECK','DELL','DG','DGX','DHI','DHR','DIS','DLR','DLTR','DOC',
    'DOV','DOW','DPZ','DRI','DTE','DUK','DVA','DVN','DXCM','EA','EBAY','ECL',
    'ED','EFX','EG','EIX','EL','ELV','EME','EMR','EOG','EPAM','EQIX','EQR',
    'EQT','ERIE','ES','ESS','ETN','ETR','EVRG','EW','EXC','EXE','EXPD','EXPE',
    'EXR','F','FANG','FAST','FCX','FDS','FDX','FE','FFIV','FICO','FIS','FISV',
    'FITB','FIX','FOX','FOXA','FRT','FSLR','FTNT','FTV','GD','GDDY','GE','GEHC',
    'GEN','GEV','GILD','GIS','GL','GLW','GM','GNRC','GOOG','GOOGL','GPC','GPN',
    'GRMN','GS','GWW','HAL','HAS','HBAN','HCA','HD','HIG','HII','HLT','HOLX',
    'HON','HOOD','HPE','HPQ','HRL','HSIC','HST','HSY','HUBB','HUM','HWM','IBKR',
    'IBM','ICE','IDXX','IEX','IFF','INCY','INTC','INTU','INVH','IP','IQV','IR',
    'IRM','ISRG','IT','ITW','IVZ','J','JBHT','JBL','JCI','JKHY','JNJ','JPM',
    'KDP','KEY','KEYS','KHC','KIM','KKR','KLAC','KMB','KMI','KO','KR','KVUE',
    'L','LDOS','LEN','LH','LHX','LII','LIN','LITE','LLY','LMT','LNT','LOW',
    'LRCX','LULU','LUV','LVS','LYB','LYV','MA','MAA','MAR','MAS','MCD','MCHP',
    'MCK','MCO','MDLZ','MDT','MET','META','MGM','MKC','MLM','MMM','MNST','MO',
    'MOS','MPC','MPWR','MRK','MRNA','MRSH','MS','MSCI','MSFT','MSI','MTB','MTD',
    'MU','NCLH','NDAQ','NDSN','NEE','NEM','NFLX','NI','NKE','NOC','NOW','NRG',
    'NSC','NTAP','NTRS','NUE','NVDA','NVR','NWS','NWSA','NXPI','O','ODFL','OKE',
    'OMC','ON','ORCL','ORLY','OTIS','OXY','PANW','PAYX','PCAR','PCG','PEG','PEP',
    'PFE','PFG','PG','PGR','PH','PHM','PKG','PLD','PLTR','PM','PNC','PNR',
    'PNW','PODD','POOL','PPG','PPL','PRU','PSA','PSKY','PSX','PTC','PWR','PYPL',
    'Q','QCOM','RCL','REG','REGN','RF','RJF','RL','RMD','ROK','ROL','ROP',
    'ROST','RSG','RTX','RVTY','SATS','SBAC','SBUX','SCHW','SHW','SJM','SLB',
    'SMCI','SNA','SNDK','SNPS','SO','SOLV','SPG','SPGI','SRE','STE','STLD','STT',
    'STX','STZ','SW','SWK','SWKS','SYF','SYK','SYY','T','TAP','TDG','TDY',
    'TECH','TEL','TER','TFC','TGT','TJX','TKO','TMO','TMUS','TPL','TPR','TRGP',
    'TRMB','TROW','TRV','TSCO','TSLA','TSN','TT','TTD','TTWO','TXN','TXT','TYL',
    'UAL','UBER','UDR','UHS','ULTA','UNH','UNP','UPS','URI','USB','V','VICI',
    'VLO','VLTO','VMC','VRSK','VRSN','VRT','VRTX','VST','VTR','VTRS','VZ','WAB',
    'WAT','WBD','WDAY','WDC','WEC','WELL','WFC','WM','WMB','WMT','WRB','WSM',
    'WST','WTW','WY','WYNN','XEL','XOM','XYL','XYZ','YUM','ZBH','ZBRA','ZTS',
]


async def translate_description(desc: str) -> str:
    """기업 소개 번역 (캐시 우선)"""
    if not desc:
        return ""
    text_hash = hashlib.md5(desc.encode()).hexdigest()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS translation_cache (
            text_hash TEXT PRIMARY KEY, original TEXT, translated TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        row = await db.execute("SELECT translated FROM translation_cache WHERE text_hash=?", (text_hash,))
        cached = await row.fetchone()
        if cached:
            return cached[0]

    prompt = f"""다음 영문 기업 소개를 한국인 투자자가 읽기 편한 자연스러운 한국어로 번역해줘.
직역이 아닌 의역으로, 한국 금융 용어를 사용해서 매끄럽게 작성해.
원문의 핵심 정보는 빠뜨리지 말고, 불필요한 수식어는 줄여서 간결하게.
번역문만 출력해.

{desc}"""
    response = await asyncio.to_thread(translate_model.generate_content, prompt)
    translated = response.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO translation_cache (text_hash,original,translated) VALUES (?,?,?)",
                         (text_hash, desc, translated))
        await db.commit()
    return translated


async def analyze_stock(ticker: str, index: int, total: int):
    """종목 하나 전체 분석 (가이던스 + 경쟁사 + 핵심지표 + 번역)"""
    t0 = time.time()
    results = {"guidance": 0, "profile": False, "translation": False}

    try:
        ov = yfinance_client.get_overview(ticker)
        company_name = ov.get('name', '')

        # 1) 경쟁사 + 핵심지표 (stock_profile_ai)
        try:
            profile = await get_stock_profile(ticker, ov)
            if profile:
                results["profile"] = True
        except Exception as e:
            log.warning(f"  [{ticker}] 프로필 실패: {e}")

        # 2) 가이던스 분석 (트랜스크립트)
        try:
            earnings = await get_full_earnings_analysis(ticker)
            history = earnings.get('history', [])
            cik = earnings.get('cik', '')

            # 이미 분석된 분기 수 확인
            async with aiosqlite.connect(DB_PATH) as db:
                row = await db.execute("SELECT COUNT(*) FROM guidance_analysis WHERE ticker=?", (ticker,))
                existing = (await row.fetchone())[0]

            if existing >= 5:
                results["guidance"] = existing
                log.info(f"  [{ticker}] 가이던스 이미 {existing}분기 캐시됨 - 스킵")
            elif history:
                guidance = await analyze_guidance_for_stock(
                    ticker, cik, history, max_quarters=20, company_name=company_name
                )
                results["guidance"] = len(guidance)
        except Exception as e:
            log.warning(f"  [{ticker}] 가이던스 실패: {e}")

        # 3) 기업 소개 번역
        try:
            desc = ov.get('description', '')
            if desc:
                await translate_description(desc)
                results["translation"] = True
        except Exception as e:
            log.warning(f"  [{ticker}] 번역 실패: {e}")

        elapsed = time.time() - t0
        log.info(f"[{index}/{total}] {ticker} 완료 - 가이던스:{results['guidance']}분기, "
                 f"프로필:{'O' if results['profile'] else 'X'}, "
                 f"번역:{'O' if results['translation'] else 'X'} [{elapsed:.0f}초]")

    except Exception as e:
        log.error(f"[{index}/{total}] {ticker} 전체 실패: {e}")


async def get_all_us_tickers():
    """Yahoo Finance에서 나스닥+NYSE 전체 종목 가져오기 (S&P 500 제외)"""
    log.info("나머지 US 종목 목록 수집 중...")
    # yfinance의 screener로 가져오기는 어려우니,
    # S&P 500 외에 사용자가 검색할 만한 인기 종목 위주로
    extra_tickers = []

    # 이미 DB에 있는 종목도 포함 (사용자가 이전에 검색한 종목)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS guidance_analysis (id INTEGER PRIMARY KEY)")
        rows = await db.execute("SELECT DISTINCT ticker FROM guidance_analysis")
        db_tickers = [r[0] for r in await rows.fetchall()]
        for t in db_tickers:
            if t not in SP500 and t not in extra_tickers:
                extra_tickers.append(t)

    log.info(f"DB에서 추가 종목 {len(extra_tickers)}개 발견")
    return extra_tickers


async def main():
    log.info("=" * 60)
    log.info("FinVision 배치 분석 시작")
    log.info(f"S&P 500: {len(SP500)}개 종목")
    log.info("=" * 60)

    # Phase 1: S&P 500
    log.info("\n── Phase 1: S&P 500 분석 ──")
    for i, ticker in enumerate(SP500, 1):
        try:
            await analyze_stock(ticker, i, len(SP500))
        except Exception as e:
            log.error(f"[{i}/{len(SP500)}] {ticker} 치명적 에러: {e}")
        await asyncio.sleep(0.5)  # rate limit 방지

    log.info("\n── Phase 1 완료 ──")

    # Phase 2: 나머지 종목 (DB에 있는 것 + 추가)
    extra = await get_all_us_tickers()
    if extra:
        log.info(f"\n── Phase 2: 추가 종목 {len(extra)}개 분석 ──")
        for i, ticker in enumerate(extra, 1):
            try:
                await analyze_stock(ticker, i, len(extra))
            except Exception as e:
                log.error(f"[{i}/{len(extra)}] {ticker} 치명적 에러: {e}")
            await asyncio.sleep(0.5)

    log.info("\n" + "=" * 60)
    log.info("배치 분석 전체 완료!")
    log.info("=" * 60)

    # 최종 통계
    async with aiosqlite.connect(DB_PATH) as db:
        g = await db.execute("SELECT COUNT(DISTINCT ticker) FROM guidance_analysis")
        g_count = (await g.fetchone())[0]
        p = await db.execute("SELECT COUNT(*) FROM stock_profile_ai")
        p_count = (await p.fetchone())[0]
        t = await db.execute("SELECT COUNT(*) FROM translation_cache")
        t_count = (await t.fetchone())[0]

    log.info(f"가이던스 분석: {g_count}개 종목")
    log.info(f"프로필(경쟁사+지표): {p_count}개 종목")
    log.info(f"번역 캐시: {t_count}건")


if __name__ == '__main__':
    asyncio.run(main())
