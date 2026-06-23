import json
import logging
from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, schema: Type[BaseModel]) -> str:
        """Generates content matching the given Pydantic schema."""
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please set it in your .env file.")
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model = model
            logger.info(f"Gemini LLM Provider initialized with model: {model}")
        except ImportError:
            raise ImportError(
                "google-genai package is required to use Gemini provider. "
                "Run `pip install google-genai` or set LLM_PROVIDER=openai in .env."
            )

    def generate(self, prompt: str, schema: Type[BaseModel]) -> str:
        from google.genai import types
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            if not response.text:
                raise ValueError("Received empty response from Gemini API")
            return response.text
        except Exception as e:
            logger.error(f"Gemini API generation error: {e}")
            raise RuntimeError(f"Gemini LLM Error: {e}") from e

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please set it in your .env file.")
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
            logger.info(f"OpenAI LLM Provider initialized with model: {model}")
        except ImportError:
            raise ImportError(
                "openai package is required to use OpenAI provider. "
                "Run `pip install openai` or set LLM_PROVIDER=gemini in .env."
            )

    def generate(self, prompt: str, schema: Type[BaseModel]) -> str:
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format=schema,
            )
            content = response.choices[0].message.content
            if not content:
                # Fallback to parsed attribute in OpenAI client schema mode
                parsed = response.choices[0].message.parsed
                if parsed:
                    return parsed.model_dump_json()
                raise ValueError("Received empty response from OpenAI API")
            return content
        except Exception as e:
            logger.error(f"OpenAI API generation error: {e}")
            raise RuntimeError(f"OpenAI LLM Error: {e}") from e

def get_llm_service() -> LLMProvider:
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    elif provider == "openai":
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            "Supported providers are 'gemini' and 'openai'."
        )
