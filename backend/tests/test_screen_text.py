"""Lesson items take the Tifinagh written on the screen, not the heard spelling."""
import main


def test_screen_text_wins_over_heard_spelling(monkeypatch, tmp_path):
    f = tmp_path / "f.jpg"; f.write_bytes(b"\xff\xd8\xff")
    frames = [(0.0, str(f)), (2.0, str(f)), (4.0, str(f))]
    vocab = {"words": [{"latin": "abaɣuɣ", "meaning_en": "fox", "t0": 0, "t1": 4}], "letters": []}
    monkeypatch.setattr(main, "_frame_choices_from_gemini", lambda chunk, options, ref_dir: [{"t": t, "choice": "A"} for t, _ in chunk])
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    import gemini_client
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": "ⴰⴱⴰⵖⵓⵖ\n"}]}}]})
    items = main.lesson_items_by_choice(frames, vocab, every=2.0)
    assert items[0]["tifinagh"] == "ⴰⴱⴰⵖⵓⵖ" and items[0]["text"] == "ⴰⴱⴰⵖⵓⵖ" and items[0]["latin_heard"] == "abaɣuɣ"
    # a different word on the screen replaces the heard one
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": "ⵉⴷⵉⴷ"}]}}]})
    items = main.lesson_items_by_choice(frames, vocab, every=2.0)
    assert items[0]["tifinagh"] == "ⵉⴷⵉⴷ" and items[0]["latin"] == "idid"


def test_unreadable_screen_keeps_heard_spelling(monkeypatch, tmp_path):
    f = tmp_path / "f.jpg"; f.write_bytes(b"\xff\xd8\xff")
    frames = [(0.0, str(f))]
    vocab = {"words": [{"latin": "abaɣuɣ", "meaning_en": "fox", "t0": 0, "t1": 4}], "letters": []}
    monkeypatch.setattr(main, "_frame_choices_from_gemini", lambda chunk, options, ref_dir: [{"t": 0.0, "choice": "A"}])
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    import gemini_client
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": "I have never seen him"}]}}]})
    items = main.lesson_items_by_choice(frames, vocab, every=2.0)
    assert items[0]["tifinagh"] == "ⴰⴱⴰⵖⵓⵖ"
