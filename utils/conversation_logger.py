"""
Simple conversation logger
Logs user and bot responses to a single file in simple format
"""

import os
from datetime import datetime
from typing import Optional

class ConversationLogger:
    def __init__(self, log_file: str = "conversation.log"):
        """
        Initialize conversation logger
        
        Args:
            log_file: Path to log file (default: conversation.log)
        """
        self.log_file = log_file
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure log file exists and create if not"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Conversation Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    def log_user(self, message: str):
        """
        Log user message
        
        Args:
            message: User's message
        """
        self._write_to_log(f"user: {message}")
    
    def log_bot(self, message: str):
        """
        Log bot response
        
        Args:
            message: Bot's response message
        """
        self._write_to_log(f"bot: {message}")
    
    def log_exchange(self, user_message: str, bot_response: str):
        """
        Log both user message and bot response together
        
        Args:
            user_message: User's message
            bot_response: Bot's response
        """
        self.log_user(user_message)
        self.log_bot(bot_response)
        self._write_to_log("")  # Empty line for separation
    
    def _write_to_log(self, content: str):
        """
        Write content to log file
        
        Args:
            content: Content to write
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
        except Exception as e:
            print(f"Warning: Failed to write to conversation log: {e}")
    
    def add_session_separator(self, session_info: Optional[str] = None):
        """
        Add a separator between conversation sessions
        
        Args:
            session_info: Optional info about the session
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        separator = f"\n--- New Session: {timestamp}"
        if session_info:
            separator += f" ({session_info})"
        separator += " ---\n"
        self._write_to_log(separator)

# Global instance for easy access
conversation_logger = ConversationLogger()

def log_user_message(message: str):
    """Convenience function to log user message"""
    conversation_logger.log_user(message)

def log_bot_response(response: str):
    """Convenience function to log bot response"""
    conversation_logger.log_bot(response)

def log_conversation_exchange(user_msg: str, bot_response: str):
    """Convenience function to log complete exchange"""
    conversation_logger.log_exchange(user_msg, bot_response)

if __name__ == "__main__":
    # Test the logger
    logger = ConversationLogger("test_conversation.log")
    
    # Test individual logging
    logger.log_user("Xin chào!")
    logger.log_bot("Chào bạn! Tôi có thể giúp gì cho bạn?")
    
    # Test exchange logging
    logger.log_exchange(
        "Làm thế nào để chăm sóc răng miệng?",
        "Để chăm sóc răng miệng tốt, bạn nên:\n1. Đánh răng 2 lần/ngày\n2. Sử dụng chỉ nha khoa\n3. Khám nha khoa định kỳ"
    )
    
    logger.add_session_separator("Test session")
    
    print("Test completed. Check test_conversation.log file.")
