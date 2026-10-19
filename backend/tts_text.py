"""What the synthetic voice should read.

The Tamazight-NLP VITS voice (Coqui, `ayymen/Coqui-TTS-Vits-Multispeaker`) only knows Tifinagh
letters: Latin input is out of vocabulary and comes out as near silence, and a vowel-less
letter-by-letter transliteration («srdgh» → ⵙⵔⴷⵖ) comes out garbled. Measured on drill 480
(«righ srdgh ifsn», 2026-10-19) by listening to the output with the ASR Space:
Latin → «ⴼ»; auto transliteration → «ⵉⵅⵙⵓⵍ ⴷ ⵖ ⵉⴼⵙⵍ»; standard spelling
«ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ» → heard back as itself.

So, in order: Tifinagh text is read as is; one or two words found in the dictionary take their
dictionary spelling; a phrase with a known meaning is put into standard orthography by Gemini
(same words, vowels written); otherwise the letter-by-letter transliteration. The speaker's own
text is never changed — this only decides what the voice reads.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from transliteration import to_forms
import lexicon

VOICE_VERSION = "v2"  # in the stored file name: older voices were made from Latin input
_TIF = re.compile(r"[ⴰ-⵿]")
_LAT = re.compile(r"[A-Za-zÀ-ɏɐ-ʯ]")


def is_tifinagh(text: str) -> bool:
    tif, lat = len(_TIF.findall(text or "")), len(_LAT.findall(text or ""))
    return tif > 0 and tif >= 4 * lat


def _lexicon_form(text: str) -> Optional[str]:
    words = text.split()
    if not 1 <= len(words) <= 2:
        return None
    hits = lexicon.lookup(text)
    if len(hits) != len(words) or not all(h.get("exact") and h.get("dictionary") for h in hits):
        return None
    forms = [(h["dictionary"][0].get("tifinagh") or "").split(",")[0].strip() for h in hits]
    if not all(forms) or not all(is_tifinagh(f) for f in forms):
        return None
    return " ".join(forms)


_SYSTEM = ("You convert ad-hoc Latin spellings of Tashlhit / Central Atlas Tamazight into standard IRCAM "
           "Tifinagh orthography with the vowels written, for a text-to-speech voice. Keep the same words in "
           "the same order; restore the vowels and particles that the spelling clearly implies (e.g. 'srdgh' "
           "→ ⵙⵙⵉⵔⴷⵖ, 'righ' → ⵔⵉⵖ). Never translate, never add other words. "
           "Answer with the Tifinagh text only, no explanation.")


def _gemini_form(text: str, meaning: str) -> Optional[str]:
    from gemini_client import gemini_generate
    answer = gemini_generate(_SYSTEM, [{"role": "user", "text": f"Spelling: «{text}»\nMeaning (Catalan): «{meaning}»"}],
                             max_output_tokens=120, temperature=0.1, timeout=40)
    out = (answer or "").strip().strip("«»\"'").strip()
    out = out.splitlines()[0].strip() if out else ""
    n_in, n_out = len(text.split()), len(out.split())
    if not out or not is_tifinagh(out) or _LAT.search(out):
        return None
    if not (max(1, n_in // 2) <= n_out <= 2 * n_in + 2):
        return None
    return out


def tts_text(text: str, meaning: Optional[str] = None) -> Tuple[str, str]:
    """(what the voice reads, how it was decided: tifinagh | lexicon | gemini | transliteration)."""
    t = (text or "").strip()
    if not t:
        return "", "empty"
    if is_tifinagh(t):
        return t, "tifinagh"
    try:
        f = _lexicon_form(t)
        if f:
            return f, "lexicon"
    except Exception:
        pass
    if meaning and meaning.strip():
        try:
            g = _gemini_form(t, meaning.strip())
            if g:
                return g, "gemini"
        except Exception as e:  # no key, quota, timeout: fall through
            print(f"[TTS TEXT] gemini normalisation failed: {e}")
    return to_forms(t)["tifinagh"], "transliteration"
