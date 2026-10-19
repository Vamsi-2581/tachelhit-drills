"""tts_text: the synthetic voice reads standard Tifinagh, never raw Latin."""
import tts_text
from test_lexicon import _fixture  # dictionary fixture (afus, fel)


def test_tifinagh_passes_through(monkeypatch):
    assert tts_text.tts_text("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ") == ("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", "tifinagh")


def test_dictionary_word_takes_its_dictionary_spelling(tmp_path, monkeypatch):
    _fixture(tmp_path, monkeypatch)
    assert tts_text.tts_text("afus") == ("ⴰⴼⵓⵙ", "lexicon")


def test_phrase_with_meaning_is_normalised_by_gemini(monkeypatch):
    monkeypatch.setattr(tts_text, "_lexicon_form", lambda t: None)
    calls = {}
    def fake(system, contents, **kw):
        calls["prompt"] = contents[0]["text"]
        return "ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ\n"
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", fake)
    spoken, how = tts_text.tts_text("righ srdgh ifsn", "Vull rentar-me les mans")
    assert (spoken, how) == ("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", "gemini") and "righ srdgh ifsn" in calls["prompt"]


def test_bad_gemini_answers_fall_back_to_transliteration(monkeypatch):
    monkeypatch.setattr(tts_text, "_lexicon_form", lambda t: None)
    import gemini_client
    for bad in ("riɣ ad ssirdɣ ifassn", "ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", ""):
        monkeypatch.setattr(gemini_client, "gemini_generate", lambda *a, **k: bad)
        spoken, how = tts_text.tts_text("righ srdgh ifsn", "Vull rentar-me les mans")
        assert how == "transliteration" and tts_text.is_tifinagh(spoken)
    def boom(*a, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(gemini_client, "gemini_generate", boom)
    assert tts_text.tts_text("righ srdgh ifsn", "x")[1] == "transliteration"
    assert tts_text.tts_text("righ srdgh ifsn")[1] == "transliteration"  # no meaning: no Gemini call
