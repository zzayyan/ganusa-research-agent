from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model: str = os.getenv("BEDROCK_MODEL", "amazon.nova-pro-v1:0")
    gemini_api_key: str = os.getenv("GOOGLE_API_KEY", "")

settings = Settings()
