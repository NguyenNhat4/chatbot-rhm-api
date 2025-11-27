import logging
from pocketflow import Flow 

# Configure logging for this module with Vietnam timezone
from utils.timezone_utils import setup_vietnam_logging
from config.logging_config import logging_config
from tracing import trace_flow, TracingConfig
from ..nodes import   (
        RetrieveFromKB, TopicClassifyAgent
)
from ..nodes import (
    IngestQuery, DecideSummarizeConversationToRetriveOrDirectlyAnswer, RagAgent, ComposeAnswer,
    FallbackNode,QueryCreatingForRetrievalAgent
)
if logging_config.USE_VIETNAM_TIMEZONE:
    logger = setup_vietnam_logging(__name__, 
                                 level=getattr(logging, logging_config.LOG_LEVEL.upper()),
                                 format_str=logging_config.LOG_FORMAT)
else:
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, logging_config.LOG_LEVEL.upper()))
    

@trace_flow(flow_name="RetrieveFlow")
class RetrievalFlow(Flow):
    def __init__(self):
        topic_classify = TopicClassifyAgent(max_retries=3, wait=2)
        retrieve_kb = RetrieveFromKB()
        fallback = FallbackNode()
        
        topic_classify >> retrieve_kb
        topic_classify - "fallback" >> fallback
        
        super().__init__(start=topic_classify)


@trace_flow(flow_name="MedFlow")
class MedFlow(Flow):
    def __init__(self):
        ingest = IngestQuery()
        main_decision = DecideSummarizeConversationToRetriveOrDirectlyAnswer()
        fallback = FallbackNode()
        rag_agent = RagAgent(max_retries=2)
        compose_answer = ComposeAnswer()
        better_retrieval_query = QueryCreatingForRetrievalAgent()
        
        # Create retrieve_flow sub-flow
        retrieve_flow = RetrievalFlow()
        
        ingest >> main_decision
        
        # Step 2: From MainDecision
        main_decision - "retrieve_kb" >> rag_agent
        # Note: "direct_response" action has NO connection -> flow ends, answer already in shared

        rag_agent - "create_retrieval_query" >> better_retrieval_query  
        better_retrieval_query >> retrieve_flow
        rag_agent - "retrieve_kb" >> retrieve_flow  # Loop back for more retrieval
        retrieve_flow >> rag_agent
        
        rag_agent - "compose_answer" >> compose_answer
        
        # Fallback  
        main_decision - "fallback" >> fallback
        rag_agent - "fallback" >> fallback
        compose_answer - "fallback" >> fallback
        better_retrieval_query - "fallback" >> fallback
        
        super().__init__(start=ingest)


def create_oqa_orthodontist_flow():
    from pocketflow import Flow 
    return Flow(start=None)

