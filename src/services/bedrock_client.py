import boto3
import time
import logging
import functools
from botocore.exceptions import ClientError, EndpointConnectionError
from src.config import settings

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


def generate_text(prompt: str) -> str:
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _get_client().converse(
                modelId=settings.bedrock_model,
                system=[{"text": "You are a precise research assistant."}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={"temperature": 0.5},
            )
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
