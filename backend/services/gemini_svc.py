from google import genai
try:
    from backend.config import GEMINI_API_KEY
except ModuleNotFoundError:
    from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def get_client():
    return client

def call_gemini(contents, model_id="gemini-1.5-flash"):
    """
    Unified call for Gemini using the new google-genai SDK.
    """
    return client.models.generate_content(
        model=model_id,
        contents=contents
    )