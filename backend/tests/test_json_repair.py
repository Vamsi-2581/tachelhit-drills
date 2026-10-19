"""_parse_json_object repairs the usual damage in a model's JSON answer."""
import main


def test_clean_and_fenced():
    assert main._parse_json_object('```json\n{"words": [{"latin": "krez"}]}\n```') == {"words": [{"latin": "krez"}]}


def test_trailing_comma():
    assert main._parse_json_object('{"words": [{"latin": "krez"},], "letters": [],}') == {"words": [{"latin": "krez"}], "letters": []}


def test_cut_off_mid_list():
    cut = '{"speech_language": "zgh", "words": [{"latin": "krez", "meaning_en": "plow", "chunk": 1}, {"latin": "ikr'
    assert main._parse_json_object(cut) == {"speech_language": "zgh", "words": [{"latin": "krez", "meaning_en": "plow", "chunk": 1}]}


def test_garbage_is_none():
    assert main._parse_json_object("I cannot help with that") is None
