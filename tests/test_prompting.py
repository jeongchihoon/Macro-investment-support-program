from src.prompting import clip_for_prompt


def test_clip_for_prompt_keeps_short_summary_intact():
    summary = (
        "SpaceX is poised for significant stock movement on July 7, 2026, due to "
        "two converging catalysts: eligibility for inclusion in the Nasdaq-100 "
        "index and the end of the 25-calendar-day quiet period for participating "
        "underwriters, allowing them to issue buy recommendations and price "
        "targets. Insider share lockups expire later."
    )

    assert clip_for_prompt(summary) == summary
    assert "buy recommendations and price targets" in clip_for_prompt(summary)


def test_clip_for_prompt_truncates_long_text_at_sentence_boundary():
    first = "First sentence has market facts. "
    second = "Second sentence has more detail. "
    long_tail = "x" * 2000

    clipped = clip_for_prompt(first + second + long_tail, limit=50)

    assert clipped == first.strip()
