"""
Configuration settings for the application
"""

import os
from typing import Optional


class ChatConfig:
    """Configuration for chat-related settings"""
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    MIN_PAGE_SIZE: int = 1
    
    # Message settings
    MAX_MESSAGE_LENGTH: int = 10000
    MAX_THREAD_NAME_LENGTH: int = 255
    
    # Default messages
    DEFAULT_WELCOME_MESSAGE: str = "Xin chào! Tôi là trợ lý AI của bạn. Rất vui được hỗ trợ bạn - Bạn cần tôi giúp gì hôm nay?"
    
    @classmethod
    def get_welcome_message(cls) -> str:
        """Get welcome message from environment or use default"""
        return os.getenv("WELCOME_MESSAGE", cls.DEFAULT_WELCOME_MESSAGE)


class LoggingConfig:
    """Configuration for logging"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Log file settings
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    MAX_LOG_SIZE: int = int(os.getenv("MAX_LOG_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))


class APIConfig:
    """Configuration for API settings"""
    
    # API versioning
    API_V1_PREFIX: str = "/api"
    
    # Rate limiting (if implemented)
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # CORS settings
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# Global config instances
chat_config = ChatConfig()
logging_config = LoggingConfig()
api_config = APIConfig()
