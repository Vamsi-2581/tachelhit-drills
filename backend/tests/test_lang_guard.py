"""keep_amazigh_lines: Darija headings written in Tifinagh never become drills; fail-open."""
import main


def test_drops_arabic_lines_keeps_amazigh(monkeypatch):
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate",
                        lambda *a, **k: '{"1": "amazigh", "2": "arabic", "3": "amazigh", "4": "other"}')
    items = [{"text": "ⴰⵔⴳⴰⵣ", "start": 1}, {"text": "ⵍⴼⵔⵇ ⴱⵉⵏ ⵃⵔⵓⴼ ⵍⵊⵔ", "start": 2},
             {"text": "ⴱ", "start": 3}, {"text": "Learn Tamazight", "start": 4}, {"text": "ⴰⵔⴳⴰⵣ", "start": 5}]
    out = main.keep_amazigh_lines(items)
    assert [i["text"] for i in out] == ["ⴰⵔⴳⴰⵣ", "ⴱ", "ⴰⵔⴳⴰⵣ"]


def test_fail_open(monkeypatch):
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    import gemini_client
    def boom(*a, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(gemini_client, "gemini_generate", boom)
    items = [{"text": "ⵍⴼⵔⵇ"}]
    assert main.keep_amazigh_lines(items) == items
    monkeypatch.setattr(main, "gemini_available", lambda: False)
    assert main.keep_amazigh_lines(items) == items
