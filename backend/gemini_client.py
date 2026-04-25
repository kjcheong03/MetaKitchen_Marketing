"""
Gemini calls: trending-topic picker (Google Search grounding) + Reel generator
(persona-conditioned, structured JSON output). Caches the persona across calls.
"""

import json
import re
from typing import Optional

from google import genai
from google.genai import types

from .config import GEMINI_API_KEY
from .persona import load_persona

_client = genai.Client(api_key=GEMINI_API_KEY)

TRENDING_MODEL = "gemini-2.5-flash"
REEL_MODEL = "gemini-2.5-flash"

_reel_schema = {
    "type": "OBJECT",
    "properties": {
        "topic": {"type": "STRING"},
        "title_slug": {"type": "STRING"},
        "hook_pattern": {
            "type": "STRING",
            "enum": [
                "named-food-contrarian",
                "hinglish-myth-buster",
                "specific-number",
                "stop-command",
                "identity-call-out",
                "credential-reversal",
                "mid-sentence-cold-open",
                "measured-proof",
            ],
        },
        "hook": {"type": "STRING"},
        "script": {"type": "STRING"},
        "caption": {"type": "STRING"},
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "compliance_check": {
            "type": "OBJECT",
            "properties": {
                "contains_banned_phrases": {"type": "BOOLEAN"},
                "has_measurable_claim": {"type": "BOOLEAN"},
                "avoids_medical_advice": {"type": "BOOLEAN"},
                "notes": {"type": "STRING"},
            },
            "required": [
                "contains_banned_phrases",
                "has_measurable_claim",
                "avoids_medical_advice",
                "notes",
            ],
        },
    },
    "required": [
        "topic",
        "title_slug",
        "hook_pattern",
        "hook",
        "script",
        "caption",
        "hashtags",
        "compliance_check",
    ],
}


def pick_trending_topic(seed_themes: Optional[list[str]] = None) -> dict:
    """Use Gemini + Google Search grounding to pick a trending metabolic-health
    topic currently popular on Indian Instagram/Facebook (past 14 days).
    Returns {topic, one_line_why, search_notes}."""
    themes = seed_themes or [
        "metabolic health",
        "blood sugar",
        "glycemic index",
        "diabetes prevention",
        "insulin sensitivity",
        "intermittent fasting",
        "fiber and gut health",
        "PCOS and insulin",
        "Indian breakfast glycemic response",
        "ghee cholesterol metabolism",
        "millets blood sugar",
        "jaggery vs sugar",
    ]
    prompt = f"""You are the content researcher for an Instagram Reel hosted by Dr Aara, an AI metabolic-health coach targeting an Indian audience on Instagram and Facebook.

Using Google Search, find ONE specific health topic that is trending or widely discussed on **Indian Instagram and Facebook in the past 14 days**. Look for:
- Viral Reels/posts by Indian health creators, dietitians, doctors
- Trending hashtags on Indian wellness IG/FB
- Recent Indian news coverage of metabolic health, diabetes, PCOS, cholesterol, Indian food glycemic response
- Comments/questions repeatedly asked under Indian health content

Themes to stay within (pick one angle):
{', '.join(themes)}

Pick a topic that:
- Has a measurable angle (GI number, grams, minutes, percent change) — not vague wellness.
- Resonates with Indian diet/lifestyle context (roti, rice, dal, chai, sweets, ghee, millets, paneer, curd, seasonal Indian foods).
- Is safe to discuss without medical advice.
- Is genuinely trending in the past 14 days on Indian social, not evergreen.
- Avoids anything requiring diagnosis or prescription.

Return JSON only:
{{
  "topic": "<one specific Indian-context topic, e.g. 'Why adding ghee to rice lowers its glycemic impact by up to 30%'>",
  "one_line_why": "<why this will stop an Indian scroller>",
  "search_notes": "<2-3 sentences citing what you saw trending — creators, posts, hashtags, or news from the past 14 days, with approximate numbers>"
}}"""

    response = _client.models.generate_content(
        model=TRENDING_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.8,
        ),
    )
    text = (response.text or "").strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    # Find JSON braces
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Could not parse topic JSON from: {text[:200]}")
    return json.loads(text[start : end + 1])


def generate_reel(topic: str, search_notes: str = "") -> dict:
    """Generate the full Reel package (script + video prompt + caption + hashtags)
    conditioned on the Dr Aara persona. Returns the structured JSON dict."""
    persona = load_persona()
    user_prompt = f"""Today's topic: {topic}

Research notes: {search_notes}

Write the complete Instagram Reel package for Dr Aara following every rule in your persona brief — the 6-beat structure (hook → why → tip → evidence → sig-close → CTA), the FSSAI April 2026 constraints, and the exact JSON output contract from section 7.

AUDIENCE: Indian adults 25–45 watching on Instagram/Facebook, often on mute. The first 1.7 seconds decide retention.

HOOK REQUIREMENTS — the hook is the single most important line in the Reel:
- Pick ONE of the 8 hook patterns in section 4a. Tag your choice in the `hook_pattern` field.
- FIRST-5-WORDS RULE (non-negotiable): the first 5 words of the script MUST contain either (a) a specific Indian food/drink noun (roti, chai, dal, poha, ghee, jaggery, curd rice, paneer, aloo, chole, idli, filter coffee, atta, maida, etc.) OR (b) a measurable number (a specific mg/dL, GI value, percentage, minute count, or gram count). That specificity IS the pattern interrupt. A pattern-interrupt verb (stop, scrap, wrong, scam, actually, mat karo) is a bonus for contrarian/myth-buster/stop-command hooks but not required — specificity alone is enough.
- The hook MUST NOT restate the tip. It creates a curiosity gap the body then closes.
- LITMUS TEST: would a bored Indian scroller recognize their own kitchen in the first 2 seconds and stop? If the hook reads like a Western lifestyle blog or a textbook, rewrite it.
- FORBIDDEN hook openers (auto-reject): "Did you know", "Studies show", "It turns out", "Here's a tip", "Let's talk about", "Have you ever wondered", "Fun fact", "In this video", "Today I want to", "Welcome back", "Aara here".

SCRIPT REQUIREMENTS:
- Target 28–32 seconds spoken = 70–78 words at speed 1.0. Hard cap 82. Hard floor 60. Count your words before returning.
- MUST begin with the hook itself (NO "Aara here!" at the start — that line is the sig-close now, not the open).
- MUST end with these two exact lines, in order: "Aara here. Follow @draara for more." — the sig-close lands AFTER the evidence peg, right before the CTA.
- Sentences ≤12 words average, hard cap 15. Short sentences create perceived pace without raising TTS speed.
- Use em-dashes ( — ) to force natural pauses. TTS reads an em-dash as a ~300ms break. Aim for 2–3 em-dashes across the script.
- Exactly ONE Hinglish switch-word per script, or zero. Approved list: galti, mat karo, walon, wala, wali, samjho, seedha, yeh, asli, bilkul. Place in hook or why line. Never two or more.
- Name specific Indian foods, not generic categories. "Poha" not "breakfast"; "ghee" not "fat"; "curd rice" not "fermented food".
- Natural spoken sentences. HeyGen reads it verbatim — no stage directions, no brackets, no list numbering, no SSML tags.
- NO banned filler phrases from section 4b ("Studies consistently show…", "is key for…", "can significantly…", "helps your body…", "aim for…" as instruction).
- Give specific numbers (GI, grams, mg/dL, percent, minutes) where you'd otherwise use vague praise.

The script flows as ONE continuous spoken passage: [hook] → [why, ≤12 words] → [tip with 1–2 specific Indian-food actions] → [evidence peg, one line] → "Aara here." → "Follow @draara for more."

Populate compliance_check honestly; if any boolean would be false, rewrite before returning."""

    response = _client.models.generate_content(
        model=REEL_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=persona,
            response_mime_type="application/json",
            response_schema=_reel_schema,
            temperature=0.95,
        ),
    )
    data = json.loads(response.text)
    _validate_compliance(data)
    _validate_voice(data)
    return data


_FILLER_PATTERNS = [
    "studies consistently show",
    "studies show consistently",
    "research consistently shows",
    "can significantly",
    "is key for",
    "plays a key role",
    "helps your body",
    "this is crucial",
    "it's important to",
    "make sure to",
]


_BLAND_HOOK_OPENERS = (
    "did you know",
    "studies show",
    "it turns out",
    "here's a tip",
    "here is a tip",
    "let's talk about",
    "have you ever wondered",
    "fun fact",
    "in this video",
    "today i want to",
    "today, i want to",
    "welcome back",
    "aara here",  # sig-close, not sig-open — must not be the first line
)


_PATTERN_INTERRUPT_VERBS = (
    "stop", "scrap", "wrong", "scam", "actually", "truth", "mat karo",
    "quit", "forget", "ditch", "skip", "drop", "kill", "bust",
)

_INDIAN_FOOD_NOUNS = (
    "roti", "chai", "dal", "poha", "ghee", "jaggery", "curd", "paneer",
    "aloo", "chole", "idli", "dosa", "upma", "atta", "maida", "rice",
    "chawal", "sabzi", "sambar", "chapati", "naan", "biryani", "khichdi",
    "lassi", "buttermilk", "chaas", "makhan", "butter", "mustard oil",
    "coconut oil", "millet", "bajra", "jowar", "ragi", "besan", "moong",
    "masoor", "chana", "rajma", "sugar", "sweets", "mithai", "halwa",
    "laddu", "barfi", "gulab jamun", "jalebi", "coffee", "milk", "curd rice",
    "filter coffee", "nariyal", "elaichi", "haldi", "hing", "jeera",
    "fruit", "banana", "mango", "apple", "orange", "juice",
)


def _validate_voice(reel: dict) -> None:
    script_raw = reel.get("script") or ""
    script = script_raw.lower()
    hook = (reel.get("hook") or "").strip().lower()

    # Sig-open is now FORBIDDEN — the hook is the first line. "Aara here"
    # belongs at the end, right before the CTA.
    script_start = script_raw.lstrip().lower()
    if script_start.startswith("aara here"):
        raise ValueError(
            "Voice fail: script must NOT start with 'Aara here'. The sig-close "
            "belongs at the end (before the CTA), not the opening. Persona §1 + §4 — regenerate."
        )

    # Length guard: we target ~30s video at speed 1.0 (~150 wpm).
    word_count = len(script_raw.split())
    if word_count > 82:
        raise ValueError(
            f"Voice fail: script is {word_count} words — overshoots 32 seconds. "
            f"Hard cap is 82 words at speed 1.0. Regenerate tighter."
        )
    if word_count < 60:
        raise ValueError(
            f"Voice fail: script is {word_count} words — under 25 seconds. "
            f"Minimum is 60 words. Add one more substantive beat or tighter evidence."
        )

    # Sig-close and CTA must both be present and in the final quarter of the script.
    if "aara here" not in script:
        raise ValueError(
            "Voice fail: script must contain the sig-close 'Aara here.' before the CTA. "
            "Persona §4 — regenerate."
        )
    if "follow @draara for more" not in script:
        raise ValueError(
            "Voice fail: script must end with 'Follow @draara for more.' — regenerate."
        )
    # Sig-close + CTA should be at the tail — last 20% of the script.
    tail_start = int(len(script) * 0.75)
    if script.find("aara here", tail_start) == -1:
        raise ValueError(
            "Voice fail: 'Aara here.' must appear in the final quarter of the script, "
            "right before the CTA — not mid-body. Regenerate."
        )

    for phrase in _FILLER_PATTERNS:
        if phrase in script:
            raise ValueError(
                f"Voice fail: filler phrase '{phrase}' in script. "
                f"Persona section 4b forbids this — regenerate."
            )

    for opener in _BLAND_HOOK_OPENERS:
        if hook.startswith(opener):
            raise ValueError(
                f"Voice fail: bland hook opener '{opener}'. "
                f"Persona §4a requires a pattern-interrupt hook — regenerate."
            )

    # First-5-words rule: hook must contain a specific Indian food noun OR a
    # measurable metric early. That specificity IS the pattern interrupt —
    # we don't also require a verb on top. Check first 8 words to allow for
    # short function-word padding at the start.
    first_words = " ".join(hook.split()[:8])
    has_food = any(noun in first_words for noun in _INDIAN_FOOD_NOUNS)
    has_metric = bool(
        re.search(
            r"\b\d+\s?(mg|gi|%|percent|grams?|minutes?|mmol|mg/dl|seconds?|hours?|kcal|calories)\b",
            first_words,
        )
        or re.search(r"\b\d{2,3}\b", first_words)  # any 2–3 digit number, e.g. "99% Indians", "GI seventy-three"
    )
    if not (has_food or has_metric):
        raise ValueError(
            "Voice fail: first 8 words of the hook must contain a specific Indian food "
            "noun (roti, chai, dal, poha, ghee, etc.) OR a measurable number. "
            "Persona §4 first-5-words rule — regenerate."
        )

    # Hook-vs-tip spoiler check: if the hook sentence appears near-verbatim
    # as the opening of the script, the hook is just restating the tip.
    if hook and len(hook) > 20 and hook[:40] in script:
        after_hook = script.split(hook[:40], 1)[-1].strip(" .,\n—")
        if after_hook[: len(hook)].startswith(hook[:20]):
            raise ValueError(
                "Voice fail: hook is restated by the next line of the script "
                "(spoiler hook). Regenerate with a gap-creating hook per §4a."
            )


def _validate_compliance(reel: dict) -> None:
    check = reel.get("compliance_check", {})
    if check.get("contains_banned_phrases") is True:
        raise ValueError(f"Compliance fail: banned phrases. Notes: {check.get('notes')}")
    if check.get("has_measurable_claim") is False:
        raise ValueError(f"Compliance fail: no measurable claim. Notes: {check.get('notes')}")
    if check.get("avoids_medical_advice") is False:
        raise ValueError(f"Compliance fail: contains medical advice. Notes: {check.get('notes')}")

    banned = [
        "100% natural", "100 % natural", "pure",
        "chemical-free", "wholesome", "superfood",
        "cures", "treats ", "heals",
        "reverses diabetes",
    ]
    script_lower = (reel.get("script") or "").lower()
    caption_lower = (reel.get("caption") or "").lower()
    for phrase in banned:
        if phrase in script_lower or phrase in caption_lower:
            raise ValueError(f"Compliance fail (string scan): banned phrase '{phrase}'")
