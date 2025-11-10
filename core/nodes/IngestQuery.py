# Core framework import
from pocketflow import Node

# Standard library imports
import logging

# Configure logging for this module with Vietnam timezone
from utils.timezone_utils import setup_vietnam_logging
from config.logging_config import logging_config

if logging_config.USE_VIETNAM_TIMEZONE:
    logger = setup_vietnam_logging(__name__, 
                                 level=getattr(logging, logging_config.LOG_LEVEL.upper()),
                                 format_str=logging_config.LOG_FORMAT)
else:
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, logging_config.LOG_LEVEL.upper()))



class IngestQuery(Node):
    def prep(self, shared):
        logger.info("🔍 [IngestQuery] PREP - Đọc role và input từ shared")
        role = shared.get("role", "")
        user_input = shared.get("input", "")
        logger.info(f"🔍 [IngestQuery] PREP - Role: {role}, Users Input : {user_input}")
        return role, user_input

    def exec(self, inputs):
        logger.info("🔍 [IngestQuery] EXEC - Xử lý role và query")
        role, user_input = inputs
        result = {"role": role, "query": user_input.strip()}
        logger.info(f"🔍 [IngestQuery] EXEC - Processed: {result}")
        return result

    def post(self, shared, prep_res, exec_res):
        logger.info("🔍 [IngestQuery] POST - Lưu role và query vào shared")
        shared["role"] = exec_res["role"]
        shared["query"] = exec_res["query"]
        logger.info(f"🔍 [IngestQuery] POST - Saved role: {exec_res['role']}, query: {exec_res['query'][:50]}...")
        return "default"

