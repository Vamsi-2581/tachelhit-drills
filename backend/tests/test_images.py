"""Drill pictures: the Gemini illustrator and the depictable rule. Shares the in-process
client (and isolated DB) of test_api.py."""
from test_api import client, main  # noqa: F401  (test_api sets the test DB before importing main)
def test_illustration_prompt_and_generate_image_endpoint(monkeypatch):
    from illustrate import illustration_prompt
    p = illustration_prompt("  Em deixes   el teu cotxe? ", hint="a small green car")
    assert "«Em deixes el teu cotxe?»" in p and "a small green car" in p
    assert "no text" in p.lower()  # the words are the drill, never the picture

    # the endpoint uses the Gemini illustrator when it is configured, and stores the upload
    d = client.post("/drills/", json={"text_catalan": "La mare fa pa"}).json()
    seen = {}
    monkeypatch.setattr(main, "illustration_available", lambda: True)
    monkeypatch.setattr(main, "generate_illustration", lambda text, hint=None: seen.setdefault("args", (text, hint)) and b"PNG")
    monkeypatch.setattr(main.cloudinary.uploader, "upload",
                        lambda data, **kw: {"secure_url": f"https://res.cloudinary.com/x/{kw.get('public_id')}.png"})
    r = client.post(f"/generate-image/{d['id']}", json={"use_ai": True, "search_query": "bread oven"})
    assert r.status_code == 200, r.text
    assert seen["args"] == ("La mare fa pa", "bread oven")
    assert r.json()["photographer"] == "Gemini illustration"
    assert client.get(f"/drills/{d['id']}").json()["image_url"].startswith("https://res.cloudinary.com/x/img_")


def test_is_depictable_draws_single_words_not_grammar_labels():
    class D:
        def __init__(self, t, tag=None): self.text_catalan, self.tag = t, tag
    assert main._is_depictable(D("carbassa"))            # one concrete word has a scene
    assert main._is_depictable(D("Em deixes el teu cotxe?"))
    assert not main._is_depictable(D("sí sí sí"))         # a chant of one word has none
    assert not main._is_depictable(D("Verb comprar - temps verbals"))
    assert not main._is_depictable(D("hola", tag="gramàtica 3"))
    assert not main._is_depictable(D(""))
