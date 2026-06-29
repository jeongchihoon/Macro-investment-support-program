from datetime import UTC, datetime

from src.causal.schema import Story
from src.causal.story import _NARRATIVE_PROMPT, _format_events_block
from src.ingest.schema import Event


def test_format_events_block_keeps_quiet_period_context_after_300_chars():
    summary = (
        "SpaceX is poised for significant stock movement on July 7, 2026, due to "
        "two converging catalysts: eligibility for inclusion in the Nasdaq-100 "
        "index, which will trigger automatic buying from index funds, and the end "
        "of the 25-calendar-day quiet period for participating underwriters, "
        "allowing them to issue buy recommendations and price targets. However, "
        "insider share lockups expire after the first quarterly earnings release."
    )
    event = Event(
        id="e1",
        title="2 Reasons July 7 Is Shaping Up as a Monster Day for SpaceX",
        summary=summary,
        occurred_at=datetime(2026, 6, 29, tzinfo=UTC),
        source_urls=["https://example.com/spacex"],
        publishers=["The Motley Fool"],
        tickers_mentioned=["SPCX"],
        spread=1,
    )
    story = Story(id="s1", event_ids=["e1"], affected_tickers=["SPCX"])

    block = _format_events_block(story, {"e1": event})

    assert "buy recommendations and price targets" in block
    assert "insider share lockups expire" in block


def test_narrative_prompt_warns_not_to_conflate_quiet_period_and_lockup():
    assert "quiet period" in _NARRATIVE_PROMPT
    assert "lock-up" in _NARRATIVE_PROMPT
    assert "보호예수" in _NARRATIVE_PROMPT
