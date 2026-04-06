from google import genai
from google.genai import types
import logging
from src.config import settings
from langsmith import traceable, get_current_run_tree

logger = logging.getLogger(__name__)

@traceable(run_type="llm")
def generate_text(prompt: str, model_id: str, max_tokens: int = 1024, temperature: float = 0.5) -> str:
    # Inject metadata for cost tracking in LangSmith natively
    run = get_current_run_tree()
    if run:
        run.metadata["ls_provider"] = "google_genai"
        run.metadata["ls_model_name"] = model_id

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        
        response = client.models.generate_content(
            model=model_id,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction="You are a precise research assistant.",
            )
        )
        
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
