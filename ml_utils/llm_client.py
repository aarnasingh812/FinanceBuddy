
import json
import logging
import re
from datetime import datetime, timezone

from django.conf import settings
from groq import Groq

from ml_utils.prompts.recommendation_prompt import (
    SYSTEM_INSTRUCTION,
    build_prompt,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 30   # seconds — generous for structured output
MAX_OUTPUT_TOKENS = 4096
MODEL_NAME = "qwen/qwen3-32b"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_narrative(context_dict: dict) -> dict | None:
    
    api_key = getattr(settings, "GROQ_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        logger.info("GROQ_API_KEY not configured — skipping LLM narrative.")
        return None

    model_name = getattr(settings, "GROQ_MODEL", MODEL_NAME)
    temperature = float(getattr(settings, "GROQ_TEMPERATURE", 0.6))

    try:
        # Build the prompt from context
        prompt_text = build_prompt(context_dict)

        # Initialize Groq client (picks up GROQ_API_KEY from env automatically,
        # but we pass it explicitly for clarity)
        client = Groq(api_key=api_key)

        # Stream the completion — collect all chunks into a single string
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user",   "content": prompt_text},
            ],
            temperature=temperature,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            top_p=0.95,
            stream=True,
            stop=None,
        )

        raw_text = ""
        for chunk in completion:
            raw_text += chunk.choices[0].delta.content or ""

        if not raw_text:
            logger.warning("Groq returned an empty response.")
            return None

        # The model may wrap its answer in <think>…</think> tags (chain-of-thought).
        # Strip anything before the first '{' to isolate the JSON object.
        json_start = raw_text.find("{")
        json_end   = raw_text.rfind("}")
        if json_start == -1 or json_end == -1:
            logger.error("No JSON object found in Groq response: %s", raw_text[:200])
            return None
        json_str = raw_text[json_start : json_end + 1]

        # Parse JSON
        narrative = json.loads(json_str)

        # Attach metadata
        narrative["model_used"] = model_name
        narrative["generated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info("LLM narrative generated successfully using %s.", model_name)
        return narrative

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Groq JSON response: %s", e)
        return None
    except Exception as e:
        logger.error("Groq API call failed: %s", e, exc_info=True)
        return None
