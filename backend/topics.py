"""Subject catalogue: what each drill is ABOUT, independent of where it came from.

`tag` says the source (a song, a lesson video, a date); `topics` says the subject a learner
or a test would look for («verbs», «salutacions», «menjar»). A fixed vocabulary, 1-3 topics
per drill, filled by Gemini from the Catalan meaning + the Tamazight text (`topics_source =
"auto"`), and overridden by hand through PUT /drills/{id} (`topics_source = "owner"`).
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Dict, List, Optional

# slug, Catalan label, hint for the classifier
TOPICS: List[dict] = [
    {"slug": "verbs", "label": "Verbs i conjugació", "hint": "a conjugated verb is the point: tense, person, aspect (I go, we ate, will you come)"},
    {"slug": "pronoms", "label": "Pronoms i possessius", "hint": "pronouns, possessives (my, yours, his house), object clitics"},
    {"slug": "preposicions", "label": "Preposicions i partícules", "hint": "in, on, with, to, from, until; directional particles"},
    {"slug": "preguntes", "label": "Preguntes", "hint": "question words and asking: what, where, who, how much, when"},
    {"slug": "negacio", "label": "Negació", "hint": "negative sentences: not, never, nobody, nothing"},
    {"slug": "numeros", "label": "Números i quantitat", "hint": "numbers, counting, how many, prices, a lot / a little"},
    {"slug": "temps-dies", "label": "Temps: hores, dies, estacions", "hint": "today, tomorrow, morning, hours, days of the week, months, seasons"},
    {"slug": "salutacions", "label": "Salutacions i cortesia", "hint": "hello, how are you, thank you, please, goodbye, welcome"},
    {"slug": "presentacions", "label": "Presentar-se", "hint": "name, age, where you live, nationality, what you do"},
    {"slug": "familia", "label": "Família i persones", "hint": "mother, father, children, husband, friend, neighbour, people"},
    {"slug": "casa", "label": "Casa i objectes", "hint": "house, rooms, furniture, everyday objects, tools"},
    {"slug": "menjar", "label": "Menjar i beguda", "hint": "food, drinks, cooking, bread, tea, meals, hunger, thirst"},
    {"slug": "cos-salut", "label": "Cos i salut", "hint": "body parts, washing, illness, pain, doctor, tired, sleep"},
    {"slug": "roba-colors", "label": "Roba i colors", "hint": "clothes, shoes, colours, size"},
    {"slug": "animals", "label": "Animals", "hint": "animals, livestock, birds, insects"},
    {"slug": "natura", "label": "Natura, muntanya i camp", "hint": "mountain, river, valley, trees, fields, farming, water, stones"},
    {"slug": "meteorologia", "label": "El temps que fa", "hint": "weather: rain, snow, wind, hot, cold, sun"},
    {"slug": "viatge", "label": "Viatge, camí i direccions", "hint": "going, road, left/right, far/near, village, car, bus, walking, running"},
    {"slug": "mercat", "label": "Mercat i compres", "hint": "buying, selling, souk, price, money, shop"},
    {"slug": "feina", "label": "Feina i oficis", "hint": "work, jobs, tools of a trade, shepherd, teacher, guide"},
    {"slug": "emocions", "label": "Emocions i opinions", "hint": "like, love, want, happy, sad, afraid, I think, beautiful, good/bad"},
    {"slug": "religio", "label": "Religió i benediccions", "hint": "God, blessings, prayer, Ramadan, Eid, good wishes"},
    {"slug": "festa-musica", "label": "Festa, música i ball", "hint": "wedding, party, ahwach, singing, dancing, drums"},
    {"slug": "aprendre", "label": "Escola i aprendre la llengua", "hint": "learning, speaking Tamazight, understanding, school, reading, writing"},
    {"slug": "alfabet", "label": "Alfabet i lletres", "hint": "a single Tifinagh letter or its name; spelling"},
    {"slug": "proverbis", "label": "Dites i proverbis", "hint": "proverbs, sayings, wisdom"},
    {"slug": "canco", "label": "Lletra de cançó", "hint": "a line of song lyrics (poetic, love, longing, homeland)"},
    {"slug": "conte", "label": "Conte i narració", "hint": "a line from a tale or story: once upon a time, the hedgehog said…"},
    {"slug": "vocabulari", "label": "Vocabulari: una paraula", "hint": "a single word or a two-word noun phrase, no sentence"},
]
SLUGS = [t["slug"] for t in TOPICS]
LABELS = {t["slug"]: t["label"] for t in TOPICS}
BATCH = 40

_state = {"running": False, "done": 0, "pending": 0, "errors": 0, "started_at": None, "finished_at": None, "last_error": None}
_lock = threading.Lock()


def parse(s: Optional[str]) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip() and x.strip() in LABELS]


def _prompt(rows: List[dict]) -> str:
    vocab = "\n".join(f"- {t['slug']}: {t['label']} — {t['hint']}" for t in TOPICS)
    items = "\n".join(
        f"- id {r['id']}: Catalan «{r.get('ca') or ''}» | Tamazight «{r.get('shi') or ''}» | source tag «{r.get('tag') or ''}»"
        for r in rows)
    return (
        "Classify each language-learning drill (a short Tamazight sentence or word with its Catalan meaning) "
        "into 1 to 3 SUBJECTS from this fixed list, most relevant first. Use ONLY these slugs. "
        "'vocabulari' only for a single word or a bare noun phrase; 'verbs' when a conjugated verb is what the "
        "drill teaches; 'canco' / 'conte' when the source tag or the text shows it is a song line or a tale line.\n\n"
        f"SUBJECTS:\n{vocab}\n\nDRILLS:\n{items}\n\n"
        "Answer ONLY with a JSON object mapping each id (as a string) to an array of slugs, e.g. "
        "{\"12\": [\"salutacions\"], \"13\": [\"verbs\", \"viatge\"]}."
    )


def classify_batch(rows: List[dict]) -> Dict[int, List[str]]:
    """rows: [{id, ca, shi, tag}] -> {id: [slugs]} (ids with no valid answer are left out)."""
    from gemini_client import gemini_generate
    answer = gemini_generate("You are a careful cataloguer of language-learning material.",
                             [{"role": "user", "text": _prompt(rows)}],
                             max_output_tokens=6000, temperature=0.1, timeout=180)
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        raise ValueError(f"no JSON in answer: {(answer or '')[:120]}")
    data = json.loads(m.group(0))
    out: Dict[int, List[str]] = {}
    for k, v in data.items():
        try:
            did = int(str(k).strip())
        except ValueError:
            continue
        slugs = [s for s in (v if isinstance(v, list) else [v]) if isinstance(s, str) and s.strip() in LABELS]
        slugs = list(dict.fromkeys(s.strip() for s in slugs))[:3]
        if slugs:
            out[did] = slugs
    return out


def status() -> dict:
    return dict(_state, topics=TOPICS)


def run(session_factory, force: bool = False, limit: int = 2000, only_ids: Optional[List[int]] = None) -> dict:
    """Fill `topics` for drills that lack it (or all, with force) in batches; runs in the caller's thread."""
    from models import Drill as DrillModel
    with _lock:
        if _state["running"]:
            return {"started": False, "reason": "already running"}
        _state.update({"running": True, "done": 0, "errors": 0, "started_at": time.time(), "finished_at": None, "last_error": None})
    try:
        db = session_factory()
        try:
            q = db.query(DrillModel)
            if only_ids:
                q = q.filter(DrillModel.id.in_(only_ids))
            elif not force:
                q = q.filter((DrillModel.topics.is_(None)) | (DrillModel.topics == ""))
            drills = q.order_by(DrillModel.id).limit(limit).all()
            if force and not only_ids:
                drills = [d for d in drills if (d.topics_source or "auto") == "auto"]  # never overwrite the owner's choice
            _state["pending"] = len(drills)
            for i in range(0, len(drills), BATCH):
                part = drills[i:i + BATCH]
                rows = [{"id": d.id, "ca": d.text_catalan, "shi": d.text_tachelhit or d.text_tachelhit_latin or d.text_tachelhit_suggested,
                         "tag": d.tag} for d in part]
                try:
                    got = classify_batch(rows)
                except Exception as e:
                    _state["errors"] += len(part); _state["last_error"] = str(e)[:200]
                    print(f"[TOPICS] batch failed: {e}")
                    continue
                for d in part:
                    slugs = got.get(d.id)
                    if slugs:
                        d.topics = ", ".join(slugs)
                        d.topics_source = "auto"
                        _state["done"] += 1
                    else:
                        _state["errors"] += 1
                db.commit()
                _state["pending"] = max(0, len(drills) - i - len(part))
                print(f"[TOPICS] {_state['done']} classified, {_state['errors']} without answer, {_state['pending']} pending")
        finally:
            db.close()
    finally:
        _state["running"] = False
        _state["finished_at"] = time.time()
    return {"started": True, "done": _state["done"], "errors": _state["errors"]}


def counts(session_factory) -> Dict[str, int]:
    from models import Drill as DrillModel
    db = session_factory()
    try:
        c: Dict[str, int] = {s: 0 for s in SLUGS}
        for (t,) in db.query(DrillModel.topics).filter(DrillModel.topics.isnot(None)).all():
            for s in parse(t):
                c[s] = c.get(s, 0) + 1
        return c
    finally:
        db.close()
