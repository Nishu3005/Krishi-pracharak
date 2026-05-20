import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client: OpenAI | None = None

TEXT_MODEL_HEAVY = "anthropic/claude-sonnet-4.6"
TEXT_MODEL_FAST  = "anthropic/claude-haiku-4.5"
IMAGE_MODEL      = "google/gemini-2.5-flash-image"


def get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("TOKEN_ROUTER_KEY")
        base_url = os.getenv("TOKEN_ROUTER_BASE_URL")
        if not key or not base_url:
            raise RuntimeError(
                "TOKEN_ROUTER_KEY and TOKEN_ROUTER_BASE_URL must be set in .env"
            )
        _client = OpenAI(api_key=key, base_url=base_url)
    return _client


def call_text(
    model: str,
    system: str,
    user: str,
    temperature: float = 0.7,
) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def call_image(model: str, prompt: str) -> str | None:
    try:
        client = get_client()
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size="1024x1024",
        )
        return response.data[0].url
    except Exception as e:
        import warnings
        warnings.warn(f"[ai_client] image generation failed: {e}")
        return None
