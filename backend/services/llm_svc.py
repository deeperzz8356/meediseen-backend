"""
Unified LLM Service with Multi-API Fallback Support
Supports: Google Gemini, OpenRouter (Qwen, Llama, Mistral, etc.), HuggingFace
"""

import base64
import io
import json
import logging
from typing import Optional, List, Any
from PIL.Image import Image

try:
    from backend.config import (
        LLM_CONFIG,
        GEMINI_TEXT_MODEL,
        OPENROUTER_TEXT_MODEL,
        OPENROUTER_VISION_MODEL,
    )
except ModuleNotFoundError:
    from config import (
        LLM_CONFIG,
        GEMINI_TEXT_MODEL,
        OPENROUTER_TEXT_MODEL,
        OPENROUTER_VISION_MODEL,
    )

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM service"""
    pass


class GeminiProvider:
    """Google Gemini API Provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.name = "gemini"
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.available = False
    
    def call(self, prompt: str, image: Optional[Image] = None, model: str = GEMINI_TEXT_MODEL) -> str:
        """Call Gemini API"""
        if not self.available:
            raise LLMError("Gemini client not available")
        
        try:
            if image:
                response = self.client.models.generate_content(
                    model=model,
                    contents=[prompt, image]
                )
            else:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt
                )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise LLMError(f"Gemini error: {str(e)}")


class OpenRouterProvider:
    """OpenRouter API Provider - supports multiple models (Qwen, Llama, Mistral, etc.)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.name = "openrouter"
        self.base_url = "https://openrouter.ai/api/v1"
        self.available = bool(api_key)
        if self.available:
            try:
                import httpx
                self.httpx = httpx
            except ImportError:
                logger.error("httpx not installed for OpenRouter")
                self.available = False
    
    def _image_to_data_url(self, image: Image) -> str:
        buffer = io.BytesIO()
        image_to_send = image.convert("RGB") if image.mode not in ("RGB", "L") else image
        image_to_send.save(buffer, format="JPEG", quality=95)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    def call(self, prompt: str, image: Optional[Image] = None, model: str = OPENROUTER_TEXT_MODEL) -> str:
        """Call OpenRouter API"""
        if not self.available:
            raise LLMError("OpenRouter not available")
        
        try:
            if image:
                model = model or OPENROUTER_VISION_MODEL
                content = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": self._image_to_data_url(image)}}
                ]
            else:
                content = prompt
            
            response = self.httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://mediseen.app",
                    "X-OpenRouter-Title": "Mediseen",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                }
            )
            
            if response.status_code != 200:
                raise LLMError(f"OpenRouter API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise LLMError(f"OpenRouter error: {str(e)}")


class HuggingFaceProvider:
    """HuggingFace Inference API Provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.name = "huggingface"
        self.base_url = "https://api-inference.huggingface.co"
        self.available = bool(api_key)
    
    def call(self, prompt: str, image: Optional[Image] = None, model: str = "mistralai/Mistral-7B-Instruct-v0.1") -> str:
        """Call HuggingFace Inference API"""
        if not self.available:
            raise LLMError("HuggingFace not available")
        
        try:
            import httpx
            
            response = httpx.post(
                f"{self.base_url}/models/{model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": prompt},
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise LLMError(f"HuggingFace API error: {response.status_code} - {response.text}")
            
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                if "generated_text" in data[0]:
                    return data[0]["generated_text"]
            
            raise LLMError(f"Unexpected response format: {data}")
        
        except Exception as e:
            logger.error(f"HuggingFace API error: {e}")
            raise LLMError(f"HuggingFace error: {str(e)}")


class LLMFallbackService:
    """
    Unified LLM Service with automatic provider fallback.
    Tries providers in order: Gemini -> OpenRouter -> HuggingFace
    """
    
    def __init__(self):
        self.providers = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        config = LLM_CONFIG["providers"]
        
        for provider_config in config:
            if not provider_config["enabled"]:
                logger.info(f"Skipping {provider_config['name']} - no API key")
                continue
            
            try:
                if provider_config["name"] == "gemini":
                    provider = GeminiProvider(provider_config["api_key"])
                    if provider.available:
                        self.providers.append(provider)
                        logger.info(f"✓ Gemini provider initialized")
                
                elif provider_config["name"] == "openrouter":
                    provider = OpenRouterProvider(provider_config["api_key"])
                    if provider.available:
                        self.providers.append(provider)
                        logger.info(f"✓ OpenRouter provider initialized")
                
                elif provider_config["name"] == "huggingface":
                    provider = HuggingFaceProvider(provider_config["api_key"])
                    if provider.available:
                        self.providers.append(provider)
                        logger.info(f"✓ HuggingFace provider initialized")
            
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_config['name']}: {e}")
        
        if not self.providers:
            raise LLMError("No LLM providers available! Check your API keys in config.")
    
    def call(self, prompt: str, image: Optional[Image] = None, preferred_provider: Optional[str] = None) -> str:
        """
        Call LLM with automatic fallback.
        
        Args:
            prompt: The prompt to send to the LLM
            image: Optional PIL Image object
            preferred_provider: Optional preferred provider name (gemini/openrouter/huggingface)
        
        Returns:
            The LLM response text
        """
        
        # Sort providers: preferred first, then others
        providers_to_try = self.providers.copy()
        if preferred_provider:
            providers_to_try.sort(key=lambda p: p.name != preferred_provider)
        
        last_error = None
        for provider in providers_to_try:
            try:
                logger.info(f"Attempting {provider.name}...")
                
                # Select model based on provider
                if provider.name == "gemini":
                    response = provider.call(prompt, image, model=GEMINI_TEXT_MODEL)
                elif provider.name == "openrouter":
                    response = provider.call(prompt, image, model=OPENROUTER_VISION_MODEL if image else OPENROUTER_TEXT_MODEL)
                elif provider.name == "huggingface":
                    response = provider.call(prompt, image, model="mistralai/Mistral-7B-Instruct-v0.1")
                else:
                    continue
                
                logger.info(f"✓ Success with {provider.name}")
                return response
            
            except LLMError as e:
                logger.warning(f"✗ {provider.name} failed: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"✗ Unexpected error with {provider.name}: {e}")
                last_error = e
                continue
        
        # All providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise LLMError(error_msg)
    
    def get_available_providers(self) -> List[str]:
        """Return list of available provider names"""
        return [p.name for p in self.providers]


# Singleton instance
_llm_service: Optional[LLMFallbackService] = None


def get_llm_service() -> LLMFallbackService:
    """Get or initialize the LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMFallbackService()
    return _llm_service


def call_llm(prompt: str, image: Optional[Image] = None, preferred_provider: Optional[str] = None) -> str:
    """
    Convenience function to call the LLM with fallback.
    
    Args:
        prompt: The prompt to send
        image: Optional PIL Image
        preferred_provider: Optional preferred provider
    
    Returns:
        The LLM response
    """
    service = get_llm_service()
    return service.call(prompt, image, preferred_provider)
