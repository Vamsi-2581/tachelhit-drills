"""dedupe_repeated_lines: a chorus becomes one drill; spelling wobbles count as the same line."""
import main


def test_repeated_lines_keep_first_only():
    segs = [{"start": 0, "end": 2, "text": "I ya-ha ya-wa aḥdadi bu muzun"},
            {"start": 2, "end": 4, "text": "Iẓṛi yumen dig-u"},
            {"start": 10, "end": 12, "text": "i ya-ha ya-wa aḥdadi bu muzun"},   # same chorus line, different case
            {"start": 12, "end": 14, "text": ""},                                  # no text: kept
            {"start": 20, "end": 22, "text_tachelhit": "ⵉⵥⵕⵉ ⵢⵓⵎⵏ ⴷⵉⴳⵓ"}]        # same line in Tifinagh
    out = main.dedupe_repeated_lines(segs)
    assert [s["start"] for s in out] == [0, 2, 12]
