from google import genai
from google.genai import types
from google.genai.errors import ServerError
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import settings
from langsmith import traceable, get_current_run_tree

logger = logging.getLogger(__name__)

# Rate-limit throttle: minimum delay between consecutive Gemini calls
_THROTTLE_DELAY = 0.5  # seconds
_last_call_time = 0.0


def _throttle():
    """Enforce a minimum delay between API calls to avoid RPM limits."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _THROTTLE_DELAY:
        time.sleep(_THROTTLE_DELAY - elapsed)
    _last_call_time = time.time()


@retry(
    retry=retry_if_exception_type((ServerError, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        f"Gemini API error, retrying in {retry_state.next_action.sleep:.1f}s "
        f"(attempt {retry_state.attempt_number}/3): {retry_state.outcome.exception()}"
    ),
)
def _call_gemini(client, model_id: str, prompt: str, max_tokens: int, temperature: float):
    """Low-level Gemini call with automatic retry on transient server errors."""
    return client.models.generate_content(
        model=model_id,
        contents=[f"System: You are a precise research assistant.\n\nUser: {prompt}"],
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    )


@traceable(run_type="llm")
def generate_text(prompt: str, model_id: str, max_tokens: int = 1024, temperature: float = 0.5) -> str:
    # Inject metadata for cost tracking in LangSmith natively
    run = get_current_run_tree()
    if run:
        run.metadata["ls_provider"] = "google_genai"
        run.metadata["ls_model_name"] = model_id

    try:
        _throttle()  # prevent RPM limit hits in rapid ReAct loops
        client = genai.Client(api_key=settings.gemini_api_key)

        response = _call_gemini(client, model_id, prompt, max_tokens, temperature)

        # Extract basic metric usages
        if run and hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            run.metadata["usage_metadata"] = {
                "input_tokens": getattr(usage, 'prompt_token_count', 0),
                "output_tokens": getattr(usage, 'candidates_token_count', 0),
                "total_tokens": getattr(usage, 'total_token_count', 0),
            }

        return response.text
    except Exception as e:
        logger.error(f"Gemini API Error ({model_id}): {e}")
        raise
