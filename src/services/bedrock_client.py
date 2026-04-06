import boto3
import time
import logging
import functools
from botocore.exceptions import ClientError, EndpointConnectionError
from src.config import settings
from langsmith import traceable, get_current_run_tree

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF = 1  # seconds


def _build_client():
    kwargs = {
        "service_name": "bedrock-runtime",
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client(**kwargs)


@functools.lru_cache(maxsize=1)
def _get_client():
    return _build_client()


@traceable(run_type="llm")
def generate_text(prompt: str, max_tokens: int = 1024, temperature: float = 0.5, model_id: str = None) -> str:
    last_error = None
    target_model = model_id or settings.bedrock_model
    
    # Inject metadata for cost tracking in LangSmith natively
    run = get_current_run_tree()
    if run:
        run.metadata["ls_provider"] = "amazon_bedrock"
        run.metadata["ls_model_name"] = target_model

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _get_client().converse(
                modelId=target_model,
                system=[{"text": "You are a precise research assistant."}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
            )
            
            # Extract basic metric usages
            usage = response.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            
            # Update LangSmith run context
            if run:
                run.metadata["usage_metadata"] = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                }
                
            return response["output"]["message"]["content"][0]["text"]

        except (EndpointConnectionError, ConnectionError) as e:
            # Network-level error — clear cached client so next attempt reconnects
            _get_client.cache_clear()
            last_error = e
            wait = BASE_BACKOFF * (2 ** (attempt - 1))
            logger.warning(
                f"Bedrock connection error (attempt {attempt}/{MAX_RETRIES}), "
                f"retrying in {wait}s: {e}"
            )
            time.sleep(wait)

        except ClientError as e:
            code = e.response["Error"]["Code"]
            # Retry on throttling / service unavailable
            if code in ("ThrottlingException", "ServiceUnavailableException", "InternalServerException"):
                last_error = e
                wait = BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    f"Bedrock {code} (attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {wait}s"
                )
                time.sleep(wait)
            else:
                # Non-retryable client error (e.g. ValidationException)
                logger.error(f"Bedrock ClientError: {e}")
                raise

        except Exception as e:
            logger.error(f"Unexpected Bedrock error: {e}")
            raise

    logger.error(f"Bedrock failed after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
