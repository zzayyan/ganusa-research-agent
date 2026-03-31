import boto3
import logging
from src.config import settings

def _get_client():
    kwargs = {
        "service_name": "bedrock-runtime",
        "region_name": settings.aws_region,
    }
    
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        
    return boto3.client(**kwargs)

client = _get_client()

def generate_text(prompt: str) -> str:
    try:
        response = client.converse(
            modelId=settings.bedrock_model,
            system=[
                {
                    "text": "You are a precise research assistant."
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "temperature": 0.5
            }
        )
        return response["output"]["message"]["content"][0]["text"]
    except Exception as e:
        logging.error(f"Error calling AWS Bedrock Converse API: {e}")
        raise
