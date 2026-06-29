"""P2 검증 — RSS 어댑터 정규화 + 수집 윈도우 필터 (오프라인 고정 fixture)."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

from ingest2.collect import rss
from ingest2.collect.rss import FeedConfig, RssCollector
from ingest2.schema import RawRecord

CFG = FeedConfig("rss_test", "http://example.com/feed", "Test Feed")


def test_normalize_builds_newsitem():
    payload = json.dumps(
        {
            "id": "abc",
            "title": "Fed holds rates",
            "summary": "<p>summary</p>",
            "link": "http://example.com/a",
            "author": "J. Doe",
            "published": "2026-06-22T12:00:00+00:00",
            "tags": ["Markets", "Fed"],
        }
    )
    raw = RawRecord(
        source_id="rss_test",
        source_native_id="abc",
        content_type="json",
        payload=payload,
        url="http://example.com/a",
        fetched_at=datetime(2026, 6, 22, 13, tzinfo=UTC),
    )
    item = RssCollector(CFG).normalize(raw)
    assert item.item_id == "rss_test:abc"
    assert item.trust_tier == 3
    assert item.title == "Fed holds rates"
    assert item.source_name == "Test Feed"
    assert item.url == "http://example.com/a"
    assert item.published_at == datetime(2026, 6, 22, 12, tzinfo=UTC)
    assert item.raw_category == "Markets,Fed"
    assert item.filter_status == "pending"


def test_normalize_extracts_google_news_publisher():
    """Google News 항목: 실제 매체를 source_name으로, 제목 꼬리 ' - WSJ' 제거."""
    payload = json.dumps(
        {
            "id": "g1",
            "title": "Stocks rally on AI optimism - WSJ",
            "summary": "...",
            "link": "https://news.google.com/rss/articles/XYZ",
            "published": "2026-06-22T12:00:00+00:00",
            "tags": [],
            "source_title": "WSJ",
            "source_href": "https://www.wsj.com",
        }
    )
    raw = RawRecord(
        source_id="rss_gnews_markets",
        source_native_id="g1",
        content_type="json",
        payload=payload,
        url="https://news.google.com/rss/articles/XYZ",
        fetched_at=datetime(2026, 6, 22, 13, tzinfo=UTC),
    )
    cfg = FeedConfig("rss_gnews_markets", "http://gnews", "Google News")
    item = RssCollector(cfg).normalize(raw)
    assert item.source_name == "WSJ"                 # 고정값 아닌 실제 매체
    assert item.title == "Stocks rally on AI optimism"  # ' - WSJ' 꼬리 제거
    assert item.source_meta["publisher_url"] == "https://www.wsj.com"
    assert item.source_meta["feed"] == "rss_gnews_markets"


def test_fetch_filters_by_window(monkeypatch):
    entries = [
        {"id": "in", "title": "in", "link": "http://x/in",
         "published_parsed": (2026, 6, 22, 12, 0, 0, 0, 0, 0)},
        {"id": "out", "title": "out", "link": "http://x/out",
         "published_parsed": (2026, 6, 1, 12, 0, 0, 0, 0, 0)},
        {"id": "", "title": "no-id", "link": ""},  # native_id 없음 → 제외
    ]
    monkeypatch.setattr(rss.feedparser, "parse", lambda url: SimpleNamespace(entries=entries))
    since = datetime(2026, 6, 22, 0, tzinfo=UTC)
    until = datetime(2026, 6, 23, 0, tzinfo=UTC)
    raws = RssCollector(CFG).fetch(since, until)
    assert [r.source_native_id for r in raws] == ["in"]
