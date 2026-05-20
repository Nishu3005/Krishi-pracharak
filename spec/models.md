# Model Selection - Token Router

All calls go through `utils/ai_client.py` using a single OpenAI-compatible client.
Model string changes per task. Base URL and key from environment.

---

## Model per Task

| Task | Model ID | Why |
|------|----------|-----|
| Targeting rationale (1 call per run) | `anthropic/claude-sonnet-4.6` | Best reasoning for multi-signal summary |
| WA message generation | `anthropic/claude-haiku-4.5` | Fast, cheap, excellent multilingual |
| SMS variant generation | `anthropic/claude-haiku-4.5` | Same |
| IVR voice script generation | `anthropic/claude-haiku-4.5` | Same |
| Rep briefing paragraph (1 call per rep) | `anthropic/claude-haiku-4.5` | Short structured output |
| Poster image generation | `google/gemini-2.5-flash-image` | Cheapest image model with good quality |

---

## Cost Expectations

- Targeting agent: 1 Sonnet call per campaign run. Negligible cost.
- Content agent: 3 Haiku calls + 1 image call per segment. For 30 segments: ~90 Haiku + 30 image calls.
- Rep agent: 1 Haiku call per rep. For a demo with 5 reps: 5 calls.

Haiku at $1/$5 per 1M tokens is cheap enough for prototype demo usage.
Gemini Flash Image at $0.30/$2.50 per 1M tokens is the lowest-cost option available.

---

## Image Prompt Structure (Gemini Flash Image)

```
Agricultural campaign poster for {crop} farmers in {state}, India.
Product: {product_name}. Growth stage: {stage_context}.
Language for text overlay: {language}.
Style: simple, high contrast, low-literacy rural audience.
Show the crop plant and product. No complex graphics.
```

---

## Fallback

Text failure: raise exception, Streamlit shows error message.
Image failure: store null in content_variants.json, show placeholder in UI, log warning.
Do not silently swallow errors.
