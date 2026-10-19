"""_align_known_lines: forced alignment of known lines through the ASR Space's /align."""
import os
import main


class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._p, self.text = status, payload, str(payload)
    def json(self):
        return self._p


def _media(tmp_path):
    f = tmp_path / "clip.mp4"; f.write_bytes(b"xx"); return str(f)


def test_lines_get_their_times_in_order(tmp_path, monkeypatch):
    seen = {}
    def fake_post(url, files=None, data=None, headers=None, timeout=None):
        seen.update(url=url, text=data["text"])
        return _Resp(200, {"segments": [{"start": 0.5, "end": 1.9, "text": "a", "words": [{"start": 0.5, "end": 1.0, "text": "ⴰⴼⵓⵙ"}]},
                                        {"start": 2.2, "end": 3.0, "text": "b"}]})
    monkeypatch.setattr(main.requests, "post", fake_post)
    out = main._align_known_lines(_media(tmp_path), ["ⴰⴼⵓⵙ ⵏⵏⴽ", "", "ⴰⴷⴰⵔ"])
    assert seen["url"].endswith("/align") and seen["text"] == "ⴰⴼⵓⵙ ⵏⵏⴽ\nⴰⴷⴰⵔ"
    assert [(o["start"], o["end"], o["text"]) for o in out] == [(0.5, 1.9, "ⴰⴼⵓⵙ ⵏⵏⴽ"), (2.2, 3.0, "ⴰⴷⴰⵔ")]
    assert out[0]["words"][0]["text"] == "ⴰⴼⵓⵙ"


def test_falls_back_on_error_or_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(404, {"detail": "Not Found"}))
    assert main._align_known_lines(_media(tmp_path), ["x"]) is None
    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp(200, {"segments": [{"start": 0, "end": 1}]}))
    assert main._align_known_lines(_media(tmp_path), ["x", "y"]) is None
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(main.requests, "post", boom)
    assert main._align_known_lines(_media(tmp_path), ["x"]) is None
    monkeypatch.setenv("ALIGN_KNOWN_TEXT", "0")
    assert main._align_known_lines(_media(tmp_path), ["x"]) is None
