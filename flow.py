from pocketflow import Flow
from nodes import (
    IngestQuery, MainAgentNode, LogConversationNode
)
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def create_med_agent_flow():
    logger.info("[Flow] Tạo simplified medical agent flow với centralized MainAgent")
    
    # Create nodes - Super simple now!
    ingest = IngestQuery()
    main_agent = MainAgentNode()
    log_conversation = LogConversationNode()
    
    logger.info("[Flow] Kết nối nodes - Linear flow")
    
    # Super simple linear flow: Ingest → MainAgent → Log
    ingest >> main_agent >> log_conversation
    
    flow = Flow(start=ingest)
    logger.info("[Flow] Simplified medical agent flow với MainAgent đã được tạo thành công")
    return flow


med_flow = create_med_agent_flow()
