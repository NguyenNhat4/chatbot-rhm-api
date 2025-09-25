"""
Script to start the Medical Conversation API server
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the API server"""
    try:
        # Check if required environment variables are set
        required_vars = ["GEMINI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            logger.info("Please set these in your .env file:")
            for var in missing_vars:
                logger.info(f"  {var}=your_value_here")
            sys.exit(1)
        
        # Import and run the API
        import uvicorn
        from api import app
        
        # Configuration
        host = os.getenv("API_HOST", "127.0.0.1")
        port = int(os.getenv("API_PORT", "8000"))
        debug = os.getenv("DEBUG", "false").lower() == "true"
        # Auto-reload by default for development, can be disabled with RELOAD=false
        reload_enabled = os.getenv("RELOAD", "true").lower() == "true"
        
        logger.info("🚀 Starting Medical Conversation API...")
        logger.info(f"🌐 Server: http://{host}:{port}")
        logger.info(f"📖 API Docs: http://{host}:{port}/docs")
        logger.info(f"📋 ReDoc: http://{host}:{port}/redoc")
        if reload_enabled:
            logger.info("🔄 Auto-reload enabled - server will restart on code changes")
        logger.info("🛑 Press Ctrl+C to stop the server")
        
        # Start the server with auto-reload
        uvicorn.run(
            "api:app",
            host=host,
            port=port,
            reload=reload_enabled,
            reload_dirs=[".", "utils", "database", "services"],  # Watch these directories
            reload_excludes=["*.log", "*.db", "__pycache__", ".git"],  # Ignore these
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
