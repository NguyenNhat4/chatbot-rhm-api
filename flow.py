from pocketflow import Flow
from nodes import (
    IngestQuery, MainDecisionAgent, ScoreDecisionNode, RetrieveFromKB, 
    ComposeAnswer, TopicSuggestResponse, ClarifyQuestionNode, GreetingResponse
)
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def create_med_agent_flow():
    logger.info("[Flow] Tạo medical agent flow với modular architecture")
    
    # Create nodes
    ingest = IngestQuery()
    main_decision = MainDecisionAgent()
    retrieve_kb = RetrieveFromKB()
    score_decision = ScoreDecisionNode()
    compose_answer = ComposeAnswer()
    topic_suggest = TopicSuggestResponse()
    clarify_question = ClarifyQuestionNode()
    greeting = GreetingResponse()
    logger.info("[Flow] Kết nối nodes theo luồng mới")
    
    # Main flow: Ingest → MainDecision
    ingest >> main_decision
    
    # From MainDecision, route based on classification
    main_decision - "retrieve_kb" >> retrieve_kb
    main_decision - "topic_suggest" >> topic_suggest
    main_decision - "greeting" >> greeting
    # From RetrieveKB, check score and decide
    retrieve_kb >> score_decision
    
    # From ScoreDecision, route to appropriate action
    score_decision - "compose_answer" >> compose_answer
    score_decision - "topic_suggest" >> topic_suggest
    score_decision - "clarify" >> clarify_question
    
   
    flow = Flow(start=ingest)
    logger.info("[Flow] Medical agent flow với modular architecture đã được tạo thành công")
    return flow


