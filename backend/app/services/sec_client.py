import requests

HEADERS = {"User-Agent": "FinVision personal-research-tool contact@example.com"}

def get_cik(ticker: str):
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt=2020-01-01&forms=10-K".format(ticker)
    # CIK 조회
    try:
        resp = requests.get(
            f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom",
            headers=HEADERS, timeout=10
        )
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            cik_elem = entry.find(".//atom:CIK", ns)
            if cik_elem is not None:
                return cik_elem.text.zfill(10)
    except:
        pass

    # 대체: company_tickers.json
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=10
        )
        tickers = resp.json()
        for _, v in tickers.items():
            if v.get("ticker", "").upper() == ticker.upper():
                return str(v["cik_str"]).zfill(10)
    except:
        pass
    return None

def get_filings(ticker: str, form_types: list = None, limit: int = 20):
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K", "DEF 14A", "SC 13G"]

    cik = get_cik(ticker)
    if not cik:
        return []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form in form_types:
                acc = accessions[i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{descriptions[i]}"
                results.append({
                    "form": form,
                    "date": dates[i],
                    "accession": accessions[i],
                    "url": filing_url,
                    "index_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=5",
                })
                if len(results) >= limit:
                    break
        return results
    except Exception as e:
        return []
