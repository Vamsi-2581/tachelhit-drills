"""Subject catalogue (topics.py): classification parsing, the run over the DB, the endpoints,
and the owner's hand-set subjects winning over the automatic ones."""
import json
import topics
from test_api import client, main  # noqa: F401


def test_parse_keeps_only_known_slugs():
    assert topics.parse("verbs, menjar, nonsense") == ["verbs", "menjar"]


def test_classify_batch_reads_gemini_json(monkeypatch):
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate",
                        lambda *a, **k: 'Here: {"1": ["verbs", "viatge", "bogus"], "2": "salutacions", "x": ["menjar"]}')
    got = topics.classify_batch([{"id": 1, "ca": "anem", "shi": "nddu", "tag": ""}, {"id": 2, "ca": "hola", "shi": "azul", "tag": ""}])
    assert got == {1: ["verbs", "viatge"], 2: ["salutacions"]}


def test_run_fills_missing_topics_and_respects_owner(monkeypatch):
    a = client.post("/drills/", json={"text_catalan": "anem a la muntanya", "text_tachelhit": "nddu s udrar"}).json()["id"]
    b = client.post("/drills/", json={"text_catalan": "hola", "text_tachelhit": "azul"}).json()["id"]
    # the owner sets b by hand: it must not be touched by a forced run
    r = client.put(f"/drills/{b}", json={"topics": "salutacions, bogus"})
    assert r.status_code == 200 and r.json()["topics"] == "salutacions" and r.json()["topics_source"] == "owner"
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate",
                        lambda *_args, **_kw: json.dumps({str(i): ["verbs", "natura"] for i in (a, b)}))
    out = topics.run(main.SessionLocal, force=True, only_ids=None, limit=5000)
    assert out["started"]
    by = {d["id"]: d for d in client.get("/drills/", params={"ids": f"{a},{b}"}).json()}
    assert by[a]["topics"] == "verbs, natura" and by[a]["topics_source"] == "auto"
    assert by[b]["topics"] == "salutacions" and by[b]["topics_source"] == "owner"
    cat = client.get("/catalog/topics").json()
    assert cat["counts"]["verbs"] >= 1 and any(t["slug"] == "verbs" for t in cat["topics"])


def test_run_endpoint_starts_a_background_run(monkeypatch):
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *a, **k: "{}")
    r = client.post("/catalog/topics/run", params={"limit": 1})
    assert r.status_code == 200 and "started" in r.json()
    import time
    for _ in range(50):
        if not client.get("/catalog/topics/status").json()["running"]:
            break
        time.sleep(0.1)
