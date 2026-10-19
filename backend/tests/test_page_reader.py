"""Page reader: narration transcript + page frame -> units with meaning; units become drafts."""
import main


def test_read_page_text_filters_and_formats(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "_space_transcribe_text", lambda p: "ⴰⵅⴰⵜⴰⵔ ⴷⴳ ⵜⵓⴷⵔⵜ ⵏ ⵓⵎⴰⵣⵉⵖ")
    import subprocess
    class R:
        stdout = "30.0"
    def fake_run(cmd, **k):
        if cmd[0] == "ffmpeg":
            open(cmd[-1], "wb").write(b"\xff\xd8\xff")
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    import gemini_client
    answer = ("ⵙⵙⵓⴼⵖ | Sortida\n"
              "ⴰⵅⴰⵜⴰⵔ ⴷⴳ ⵜⵓⴷⵔⵜ ⵏ ⵓⵎⴰⵣⵉⵖ. | Important en la vida de l'amazic.\n"
              "ⵉⵎⵉⵙ ⵉⵎⵉⵙ ⵉⵎⵉⵙ ⵉⵎⵉⵙ | Imis\n"
              "no pipe\n"
              "latin only | res\n")
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": answer}]}}]})
    lines = main.read_page_text("v.mp4", str(tmp_path))
    assert lines == ["ⵙⵙⵓⴼⵖ | Sortida", "ⴰⵅⴰⵜⴰⵔ ⴷⴳ ⵜⵓⴷⵔⵜ ⵏ ⵓⵎⴰⵣⵉⵖ. | Important en la vida de l'amazic."]


def test_no_narration_means_no_page_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "_space_transcribe_text", lambda p: "")
    assert main.read_page_text("v.mp4", str(tmp_path)) == []


def test_page_segments_become_drafts():
    segs = [{"start": 0, "end": 2, "text": "ⴰⵅⴰⵜⴰⵔ", "text_tachelhit": "ⴰⵅⴰⵜⴰⵔ", "text_catalan": "Important"}]
    out = main.page_segments_to_drafts(segs)
    assert out[0]["text_tachelhit_suggested"] == "ⴰⵅⴰⵜⴰⵔ" and out[0]["text_tachelhit"] is None and out[0]["text"] == "" and out[0]["text_catalan"] == "Important"
