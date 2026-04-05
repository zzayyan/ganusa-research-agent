from google import genai
from google.genai import types
import logging
from src.config import settings

logger = logging.getLogger(__name__)

def generate_text(prompt: str, model_id: str, max_tokens: int = 1024, temperature: float = 0.5) -> str:
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
        return response.text
    except Exception as e:
        logger.error(f"Gemini API Error ({model_id}): {e}")
        raise
