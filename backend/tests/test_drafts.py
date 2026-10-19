"""Meaning check of machine drafts (draft_check.py + /drafts endpoints)."""
import json

import draft_check
from test_api import client, main  # noqa: F401  (shared app + DB fixtures)


def test_clean_draft_and_status():
    assert draft_check._clean_draft("[? Wana yijlan, fkas afus | wana yijla]") == "Wana yijlan, fkas afus"
    rec = json.dumps({"draft": "wana yijlan", "verdict": "no"})
    assert draft_check.draft_status(rec, "[? wana yijlan]") == "no"
    assert draft_check.draft_status(rec, "[? something else]") == "unchecked"  # the draft changed
    assert draft_check.draft_status(None, "x") == "unchecked"


def test_check_draft_meaning_uses_blind_translation_then_judge(monkeypatch):
    calls = []

    def fake_generate(system, contents, **kw):
        calls.append(contents[0]["text"])
        if len(calls) == 1:
            assert "T'ho he deixat tot" not in contents[0]["text"]  # the translation is blind
            return "[asir] [awalla] a tu [sers]"
        return '{"verdict": "no", "confidence": 0.9, "note": "no són paraules amazigues"}'

    monkeypatch.setattr(draft_check, "gemini_available", lambda: True)
    monkeypatch.setattr(draft_check, "gemini_generate", fake_generate)
    rec = draft_check.check_draft_meaning("[? asir awalla yennik sers]", {"català": "T'ho he deixat tot", "àrab": "لقد تركت لك كل شيء"})
    assert rec["verdict"] == "no" and rec["draft"] == "asir awalla yennik sers" and rec["back_translation"].startswith("[asir]")
    assert len(calls) == 2
    assert draft_check.check_draft_meaning("", {"català": "x"}) is None
    assert draft_check.check_draft_meaning("[? abc]", {}) is None


def test_check_endpoint_stores_verdict_and_tutor_context_refuses(monkeypatch):
    monkeypatch.setattr(main, "check_draft_meaning", lambda draft, meanings, onscreen=None: {
        "draft": "asir awalla yennik sers", "back_translation": "?", "verdict": "no", "confidence": 0.9, "note": "n", "checked_at": "t"})
    r = client.post("/drills/", json={"text_catalan": "T'ho he deixat tot", "text_tachelhit_suggested": "[? asir awalla yennik sers]"})
    assert r.status_code in (200, 201), r.text
    did = r.json()["id"]
    r = client.post(f"/drafts/check/{did}")
    assert r.status_code == 200 and r.json()["verdict"] == "no"
    d = client.get(f"/drills/{did}").json()
    assert json.loads(d["draft_check"])["verdict"] == "no"
    # the tutor's context tells it not to explain the failed draft
    from test_api import main as m
    db = m.SessionLocal()
    try:
        drill = db.query(m.DrillModel).filter(m.DrillModel.id == did).first()
        ctx = m._drill_context(drill)
    finally:
        db.close()
    assert "NO quadra" in ctx and "NO l'expliquis" in ctx
    # a drill with speaker text has nothing to check
    r = client.post("/drills/", json={"text_catalan": "la mà", "text_tachelhit": "ⴰⴼⵓⵙ"})
    assert client.post(f"/drafts/check/{r.json()['id']}").json()["status"] == "nothing_to_check"
