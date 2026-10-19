"""Subtitle cues that carry the Tachelhit line with the English meaning in parentheses."""
from test_api import main  # noqa: F401


def test_line_with_parenthesised_gloss_is_split():
    text, gloss, lang = main.split_bilingual_cue("I ya-ha ya-wa ! tinew a tinew da (Oh, my story ...)")
    assert text == "I ya-ha ya-wa ! tinew a tinew da" and gloss == "Oh, my story ..." and lang == "en"
    text, gloss, lang = main.split_bilingual_cue("Uchen ad ittch tasa-nnem (The wolf will devour your liver)")
    assert text.startswith("Uchen ad ittch") and gloss.startswith("The wolf")


def test_plain_english_cue_with_parenthesis_is_not_split():
    text, gloss, lang = main.split_bilingual_cue("Come to Madraba (near Agadir)")
    assert gloss is None and text == "Come to Madraba (near Agadir)"
    text, gloss, lang = main.split_bilingual_cue("Have you been to Aourir ?")
    assert gloss is None
