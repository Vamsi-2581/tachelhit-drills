---
title: ASR MMS (Amazigh varieties)
emoji: 🎙️
colorFrom: indigo
colorTo: yellow
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: cc-by-nc-4.0
---

# MMS ASR for Amazigh varieties

Meta **MMS-1B-all** with the per-language adapters **shi** (Tachelhit), **kab** (Kabyle)
and **taq** (Tamasheq). Standard Moroccan / Central Atlas Tamazight has no MMS adapter;
the org's NeMo FastConformer Space (`Tamazight-NLP/ASR`) covers it.

Endpoint: `/transcribe(audio, lang)` → text. Created for the Tachelhit Drills ASR
bake-off (which model to trust for which variety). Model licence: CC-BY-NC 4.0.
