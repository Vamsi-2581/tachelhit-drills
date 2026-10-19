"""Meaning check for machine drafts of Tamazight speech.

A draft is what a listener (Gemini audio, the ASR Space) wrote for a clip. Tamazight
listening is weak, so a draft can be a Tamazight-looking string that means nothing
("asir awalla yennik sers" for "I left you everything"). We hold an independent truth
for most clips — the subtitle the clip was cut from, the on-screen Tifinagh, the lyrics,
a gloss — so the draft can be checked instead of trusted:

1. translate the draft on its own, with no hint of the expected meaning (blind);
2. ask a judge whether that translation and the known meaning say the same thing.

The verdict is stored on the drill (`draft_check`, JSON) and the app shows a draft to
learners only when it passes. A failed draft stays in the editor and the verification
queue for a speaker to replace. Two short text calls per draft.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from gemini_client import gemini_available, gemini_generate

VERDICTS = ("yes", "roughly", "no")


def _clean_draft(draft: str) -> str:
    """Drop the machine-listening bracket and alternatives: "[? a | b]" -> "a"."""
    d = (draft or "").strip()
    d = d.replace("[?", " ").replace("[", " ").replace("]", " ")
    if "|" in d:
        d = d.split("|", 1)[0]
    if " · " in d:
        d = d.split(" · ", 1)[0]
    return re.sub(r"\s+", " ", d).strip()


def _blind_translation(draft: str) -> str:
    system = ("Ets un traductor de taixelhit / tamazight (amazic del Marroc) al català. Tradueix el text tal com és. "
              "Si una paraula no és cap paraula amaziga que coneguis, escriu-la entre claudàtors tal qual. "
              "Respon NOMÉS amb la traducció.")
    return gemini_generate(system, [{"role": "user", "text": draft}], max_output_tokens=120, temperature=0.1).strip()


def _judge(draft: str, back: str, meanings: Dict[str, str], onscreen: Optional[str]) -> Dict:
    known = "\n".join(f"- {k}: {v}" for k, v in meanings.items() if v)
    if onscreen:
        known += f"\n- text que apareix en pantalla al vídeo: {onscreen}"
    system = ("Jutges si una lectura automàtica d'un enregistrament en tamazight diu el mateix que el significat conegut. "
              "Respon NOMÉS amb JSON: {\"verdict\": \"yes\"|\"roughly\"|\"no\", \"confidence\": 0-1, \"note\": \"<= 15 paraules\"}. "
              "yes = la lectura, tal com s'ha traduït a cegues, expressa el mateix; roughly = hi ha paraules clau en comú però "
              "no tot; no = no hi té res a veure, o la lectura no són paraules amazigues reals. Sigues estricte: una lectura que "
              "només s'assembla en la forma però no en el sentit és 'no'.")
    user = (f"Lectura automàtica: «{draft}»\nTraducció a cegues de la lectura: «{back}»\nSignificat conegut:\n{known}")
    out = gemini_generate(system, [{"role": "user", "text": user}], max_output_tokens=120, temperature=0.0)
    m = re.search(r"\{.*\}", out, re.S)
    data = json.loads(m.group(0)) if m else {}
    verdict = str(data.get("verdict", "")).lower().strip()
    if verdict not in VERDICTS:
        verdict = "no"
    try:
        conf = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    return {"verdict": verdict, "confidence": conf, "note": str(data.get("note", ""))[:160]}


def check_draft_meaning(draft: str, meanings: Dict[str, str], onscreen: Optional[str] = None) -> Optional[Dict]:
    """Returns the stored record, or None when there is nothing to check against
    (no draft, no known meaning, or Gemini unavailable)."""
    text = _clean_draft(draft)
    meanings = {k: (v or "").strip() for k, v in (meanings or {}).items() if (v or "").strip()}
    if not text or not (meanings or onscreen) or not gemini_available():
        return None
    back = _blind_translation(text)
    verdict = _judge(text, back, meanings, onscreen)
    return {
        "draft": text,
        "back_translation": back,
        **verdict,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def draft_status(draft_check_json: Optional[str], current_draft: Optional[str]) -> str:
    """'yes' | 'roughly' | 'no' | 'unchecked' for the draft currently on the drill."""
    if not draft_check_json or not (current_draft or "").strip():
        return "unchecked"
    try:
        rec = json.loads(draft_check_json)
    except (TypeError, ValueError):
        return "unchecked"
    if rec.get("draft") != _clean_draft(current_draft):
        return "unchecked"  # the draft changed since the check
    return rec.get("verdict") if rec.get("verdict") in VERDICTS else "unchecked"
