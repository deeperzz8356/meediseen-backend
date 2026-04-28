import os
from dotenv import load_dotenv

load_dotenv()

# ========================================
# API Keys for Multiple LLM Providers
# ========================================

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

# OpenRouter (supports multiple models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_TEXT_MODEL = os.getenv("OPENROUTER_TEXT_MODEL", "qwen/qwen-2.5-72b-instruct")
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")

# HuggingFace Inference API
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# ========================================
# LLM Model Configuration
# ========================================
LLM_CONFIG = {
    "providers": [
        {
            "name": "gemini",
            "api_key": GEMINI_API_KEY,
            "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "enabled": bool(GEMINI_API_KEY)
        },
        {
            "name": "openrouter",
            "api_key": OPENROUTER_API_KEY,
            "models": [
                "qwen/qwen-2.5-72b-instruct",  # Qwen free model
                "meta-llama/llama-2-70b-chat",  # Llama 2
                "mistralai/mistral-7b-instruct",  # Mistral
                "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",  # Nous Hermes
            ],
            "enabled": bool(OPENROUTER_API_KEY)
        },
        {
            "name": "huggingface",
            "api_key": HUGGINGFACE_API_KEY,
            "models": [
                "mistralai/Mistral-7B-Instruct-v0.1",
                "meta-llama/Llama-2-70b-chat-hf",
            ],
            "enabled": bool(HUGGINGFACE_API_KEY)
        }
    ]
}
