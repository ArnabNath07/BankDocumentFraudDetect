from pydantic import BaseModel
import os
from dotenv import load_dotenv  # added

load_dotenv()  # loads variables from .env

class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    llm_model: str = "openai/gpt-oss-20b"  # adjust to any Groq-supported model
    enable_llm: bool = True

settings = Settings()
