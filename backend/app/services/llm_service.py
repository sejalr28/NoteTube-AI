"""
llm_service.py
----------------
Thin wrapper around the Groq LLM API (OpenAI-compatible interface).

AI/ML concept demonstrated: LLM INTEGRATION.
This is the "Generation" half of RAG -- once we've retrieved relevant
chunks, we hand them to a large language model along with the user's
question, and the LLM produces a natural-language answer grounded in
that context.

Why isolate this in its own file:
If we wanted to swap Groq for OpenAI or Gemini, we'd only need to change
this ONE file. Every other file (rag_service.py, chat_routes.py, etc.)
just calls `generate_completion(prompt)` and doesn't care which provider
is behind it. This is a simple but real example of the "adapter" pattern.
"""

from groq import Groq
from app.config import settings

_client = Groq(api_key=settings.GROQ_API_KEY)


def generate_completion(prompt: str, temperature: float = 0.3, model: str | None = None) -> str:
    """
    Sends a prompt to the LLM and returns its text response.

    temperature=0.3 (fairly low) is intentional: for Q&A and summarization
    grounded in a transcript, we want factual, consistent answers rather
    than creative/random ones. Higher temperature = more randomness.
    """
    model = model or settings.LLM_MODEL

    extra = {}
    if model.startswith("openai/gpt-oss"):
        # gpt-oss models are reasoning models: their hidden reasoning tokens
        # count against max_tokens, and at the default effort they can use up
        # the whole budget and return an EMPTY answer. "low" avoids that.
        extra["extra_body"] = {"reasoning_effort": "low"}

    try:
        response = _client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048,
            **extra,
        )
        content = (response.choices[0].message.content or "").strip()

    except Exception as e:
        # Surface a clean error rather than letting the raw SDK exception
        # bubble up to the client.
        raise RuntimeError(f"LLM request failed: {str(e)}")

    if not content:
        raise RuntimeError("LLM returned an empty response. Please try again.")
    return content
