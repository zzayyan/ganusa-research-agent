import logging
from src.services.bedrock_client import generate_text as bedrock_generate
from src.services.gemini_client import generate_text as gemini_generate
from src.config import settings

logger = logging.getLogger(__name__)

def generate_text(prompt: str, model_id: str = None, max_tokens: int = 1024, temperature: float = 0.5) -> str:
    if not model_id:
        model_id = settings.bedrock_model

    if "gemini" in model_id.lower() or "gemma" in model_id.lower():
        return gemini_generate(prompt, model_id, max_tokens, temperature)
    else:
        return bedrock_generate(prompt, max_tokens, temperature, model_id=model_id)