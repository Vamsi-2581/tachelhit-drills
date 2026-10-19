"""merge_subtitle_frames: Amazigh-only subtitles (no translation line anywhere) are kept;
in multilingual subtitles a line without translation is still dropped as a title."""
import main


def _frames(lines_by_t):
    return [{"t": t, "lines": [{"lang": l, "text": x} for l, x in ls]} for t, ls in lines_by_t]


def test_tifinagh_only_subtitles_become_cues():
    items = _frames([(0, [("zgh", "ⵜⴰⵎⴰⵣⵉⵖⵜ ⴷ ⵜⵓⵜⵍⴰⵢⵜ")]), (1, [("zgh", "ⵜⴰⵎⴰⵣⵉⵖⵜ ⴷ ⵜⵓⵜⵍⴰⵢⵜ")]),
                     (2, [("zgh", "ⵜⴰⵎⴰⵣⵉⵖⵜ ⴷ ⵜⵓⵜⵍⴰⵢⵜ")]), (3, [("zgh", "ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ")]), (4, [("zgh", "ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ")])])
    cues = main.merge_subtitle_frames(items, every=1.0)
    assert [c["text"] for c in cues] == ["ⵜⴰⵎⴰⵣⵉⵖⵜ ⴷ ⵜⵓⵜⵍⴰⵢⵜ", "ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ"]
    assert cues[0]["tifinagh"] == "ⵜⴰⵎⴰⵣⵉⵖⵜ ⴷ ⵜⵓⵜⵍⴰⵢⵜ" and cues[0]["gloss"] is None and cues[0]["gloss_lang"] is None


def test_multilingual_subtitles_still_drop_untranslated_titles():
    items = _frames([(0, [("shi", "Tasuta n Imal")]), (1, [("shi", "Tasuta n Imal")]),
                     (2, [("shi", "tinew a tinew"), ("en", "my sisters")]), (3, [("shi", "tinew a tinew"), ("en", "my sisters")])])
    cues = main.merge_subtitle_frames(items, every=1.0)
    assert [c["text"] for c in cues] == ["tinew a tinew"]
