import json
import os
from datetime import datetime

from utils.ai_client import call_text, call_image, TEXT_MODEL_FAST, IMAGE_MODEL
from utils.product_catalog import get_product_context

DATA_DIR = "data"
OUTPUT_PATH = os.path.join(DATA_DIR, "content_variants.json")

PERSONA_TONE = {
    "hot_lead":              "The farmer already scanned this product. Use a direct conversion CTA — they know the product, push them to buy now from their local retailer.",
    "pre_stage_alert":       "Urgent. A critical crop stage is approaching. Emphasise that acting now will protect their crop. Time-sensitive tone.",
    "offline_reinforcement": "The farmer attended a Syngenta field event. Reinforce what they learned. Warm, familiar tone — like a follow-up from someone they met.",
    "awareness":             "Educational and trustworthy. Introduce the product benefit clearly. Simple language. Do not assume prior product knowledge.",
}

LANGUAGE_NOTES = {
    "Hindi":   "Write in simple, conversational Hindi. Use Devanagari script. Avoid complex vocabulary.",
    "Punjabi": "Write in Punjabi using Gurmukhi script. Warm, direct tone.",
    "Marathi": "Write in Marathi using Devanagari script. Respectful, farmer-friendly tone.",
    "Gujarati":"Write in Gujarati script. Clear and practical.",
    "Kannada": "Write in Kannada script. Simple and respectful.",
    "Bengali": "Write in Bengali script. Friendly and clear.",
}


def run_content_generation(targeting_plan: dict) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)

    variants = {}
    segments = targeting_plan.get("segments", [])

    for seg in segments:
        if not seg.get("inventory_ok", True):
            continue

        seg_id = seg["segment_id"]
        variants[seg_id] = _generate_segment_content(seg)

    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "variants": variants,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output


def _generate_segment_content(seg: dict) -> dict:
    language  = seg.get("language", "Hindi")
    persona   = seg.get("persona", "awareness")
    product   = seg.get("product", "")
    crop      = seg.get("crop", "")
    state     = seg.get("state", "")
    channel   = seg.get("channel", "whatsapp")
    stage_ctx = seg.get("stage_context", "")

    product_info = get_product_context(product)
    tone_note    = PERSONA_TONE.get(persona, PERSONA_TONE["awareness"])
    lang_note    = LANGUAGE_NOTES.get(language, LANGUAGE_NOTES["Hindi"])

    context_block = (
        f"Crop: {crop}. Region: {state}, India. Growth stage context: {stage_ctx}. "
        f"Product: {product} ({product_info.get('type','')}) — targets {product_info.get('target','')}. "
        f"Application: {product_info.get('application','')}."
    )

    wa_text   = _gen_whatsapp(context_block, tone_note, lang_note, language) if channel == "whatsapp" else None
    sms_text  = _gen_sms(context_block, tone_note, lang_note, language)
    ivr_text  = _gen_ivr(context_block, tone_note, lang_note, language)
    poster_prompt = _build_poster_prompt(crop, product, state, language, stage_ctx, persona)
    poster_url    = call_image(IMAGE_MODEL, poster_prompt)

    return {
        "language":         language,
        "persona":          persona,
        "whatsapp":         wa_text,
        "sms":              sms_text,
        "ivr_script":       ivr_text,
        "poster_image_url": poster_url,
        "poster_prompt_used": poster_prompt,
        "models_used": {
            "text":  TEXT_MODEL_FAST,
            "image": IMAGE_MODEL,
        },
    }


def _gen_whatsapp(context: str, tone: str, lang_note: str, language: str) -> str:
    system = "You are a Syngenta agricultural marketing copywriter specialising in rural farmer communication."
    user = f"""{context}

Tone instruction: {tone}
Language instruction: {lang_note}

Write a WhatsApp message for this farmer segment. Requirements:
- Maximum 200 characters
- Must be in {language}
- Include the product name naturally
- End with a clear action (ask retailer / apply now / call helpline)
- No hashtags. No formal salutation. Direct and warm.

Return only the message text."""
    return call_text(TEXT_MODEL_FAST, system, user, temperature=0.75)


def _gen_sms(context: str, tone: str, lang_note: str, language: str) -> str:
    system = "You are a Syngenta agricultural marketing copywriter specialising in rural farmer communication."
    user = f"""{context}

Tone instruction: {tone}
Language instruction: {lang_note}

Write an SMS message for this farmer segment. Requirements:
- Maximum 120 characters
- Must be in {language}
- No emoji. Feature-phone compatible.
- Include the product name and one clear action

Return only the SMS text."""
    return call_text(TEXT_MODEL_FAST, system, user, temperature=0.7)


def _gen_ivr(context: str, tone: str, lang_note: str, language: str) -> str:
    system = "You are a Syngenta agricultural marketing copywriter specialising in rural farmer communication."
    user = f"""{context}

Tone instruction: {tone}
Language instruction: {lang_note}

Write a 30-second IVR (voice call) script for this farmer segment. Requirements:
- Spoken naturally, as if read aloud by a warm voice
- Must be in {language}
- Approximately 60-80 words
- Open with a greeting relevant to the farming season
- Mention the crop stage, the risk, and the product as the solution
- Close with: "Ask for [product name] at your nearest Syngenta retailer."

Return only the script text."""
    return call_text(TEXT_MODEL_FAST, system, user, temperature=0.7)


def _build_poster_prompt(
    crop: str, product: str, state: str, language: str, stage_ctx: str, persona: str
) -> str:
    urgency = "urgent, time-sensitive" if persona == "pre_stage_alert" else "informative, trustworthy"
    return (
        f"Agricultural campaign poster for {crop} farmers in {state}, India. "
        f"Product: {product}. Growth stage: {stage_ctx}. "
        f"Mood: {urgency}. "
        f"Include text overlay in {language} language. "
        f"Style: simple, high contrast, suitable for low-literacy rural audience. "
        f"Show the {crop} plant and product packaging. Clean layout, bold text, no complex graphics."
    )
