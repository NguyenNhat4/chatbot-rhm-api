import os
import logging
import re
from google import genai
from dotenv import load_dotenv
load_dotenv()
# Configure logging for this module
logger = logging.getLogger(__name__)
from google.genai import types

class APIOverloadException(Exception):
    """Exception raised when API is overloaded or quota exceeded"""
    pass

# Initialize client at module level to avoid overhead on each call
api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    logger.error(" GEMINI_API_KEY is not set")
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for Vietnamese and English text.
    Uses a simple heuristic: ~4 characters per token for Vietnamese, ~3.5 for English.
    This is a rough approximation for logging purposes.
    """
    if not text:
        return 0
    
    # Count Vietnamese characters (with diacritics)
    vietnamese_chars = len(re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]', text))
    # Count total characters
    total_chars = len(text)
    
    # Rough estimation: Vietnamese text tends to have more tokens per character
    if vietnamese_chars > total_chars * 0.1:  # If >10% Vietnamese chars
        estimated_tokens = int(total_chars / 3.2)  # Vietnamese: ~3.2 chars per token
    else:
        estimated_tokens = int(total_chars / 3.8)  # English: ~3.8 chars per token
    
    return max(1, estimated_tokens)


# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt: str, fast_mode: bool = True) -> str:
    logger.info("🤖 Bắt đầu gọi LLM...")
    
    # Log token count before API call
    estimated_tokens = estimate_tokens(prompt)
    logger.info(f"📊 Estimated input tokens: {estimated_tokens} (prompt length: {len(prompt)} chars)")
    
    # Dynamic model selection based on fast_mode
    if fast_mode:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-8b")  # Super fast
    else:
        model = os.getenv("GEMINI_MODEL_QUALITY", "gemini-2.5-flash")  # High quality
    
    logger.info(f"🎯 Using model: {model}")
    
    try:
        logger.info("⏳ Đang gửi request đến Gemini...")
        response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.5,
            top_p=0.9
        ),
    )
            
        response_text = response.text
        
        # Handle case where response.text is None
        if response_text is None:
            logger.warning("⚠️ Response text is None, checking response object...")
            logger.info(f"Response object: {response}")
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"Candidates: {response.candidates}")
                if response.candidates[0].content and response.candidates[0].content.parts:
                    response_text = response.candidates[0].content.parts[0].text
                    logger.info(f"✅ Extracted text from candidates: {len(response_text)} characters")
                else:
                    logger.error("❌ No text found in candidates")
                    response_text = "Xin lỗi, không thể tạo response."
            else:
                logger.error("❌ No candidates in response")
                response_text = "Xin lỗi, không thể tạo response."
        
        if response_text:
            output_tokens = estimate_tokens(response_text)
            logger.info(f"✅ Nhận được response từ LLM: {len(response_text)} characters")
            logger.info(f"📊 Estimated output tokens: {output_tokens}")
            logger.info(f"📤 Response preview: {response_text[:200]}...")
            logger.info(f"🔍 Full response for debugging: {response_text}")

        return response_text or "Xin lỗi, không thể tạo response."
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Lỗi khi gọi LLM: {error_str}")
        
        # Handle quota exceeded and API overload specifically
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            logger.warning("⚠️ Gemini API quota exceeded or overloaded. Triggering fallback mode.")
            raise APIOverloadException("API quota exceeded")
        
        # Handle other API errors
        if "500" in error_str or "503" in error_str or "overload" in error_str.lower():
            logger.warning("⚠️ API server overloaded. Triggering fallback mode.")
            raise APIOverloadException("API server overloaded")
        
        # For other errors, still return fallback message instead of raising
        logger.warning("⚠️ Unexpected API error. Using fallback response.")
        return "Xin lỗi hiện tại mình đang bị quá tải bạn chờ một chút nhé."

if __name__ == "__main__":
    test_prompt = "Hello, how are you?"
    print(call_llm(test_prompt))
