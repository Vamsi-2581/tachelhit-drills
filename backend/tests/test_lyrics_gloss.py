"""Lyrics with meanings: the gloss rides along with the aligned line."""
from test_api import main  # noqa: F401


def test_align_lyrics_lines_keeps_the_meaning_as_a_gloss():
    segs = [{"start": 0.0, "end": 2.0, "text": "tu merti wad isfliden"}, {"start": 2.0, "end": 4.0, "text": "gur may sawal"}]
    out = main._align_lyrics_lines(segs, "tu mertiwa day sfliden | M'estàs escoltant\ngur may sawal | No parlis")
    assert out[0]["text"] == "tu mertiwa day sfliden" and out[0]["gloss"] == "M'estàs escoltant" and out[0]["gloss_lang"] == "ca"
    assert out[1]["text"] == "gur may sawal" and out[1]["gloss"] == "No parlis"
    assert out[0]["text_asr"] == "tu merti wad isfliden"


def test_align_lyrics_lines_without_meanings_unchanged():
    segs = [{"start": 0.0, "end": 2.0, "text": "x"}]
    out = main._align_lyrics_lines(segs, "nekkin dderkiyi n tted")
    assert out[0]["text"] == "nekkin dderkiyi n tted" and "gloss" not in out[0]
