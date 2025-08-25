from pocketflow import Node
from utils.call_llm import call_llm
from utils.kb import retrieve
from utils.conversation_logger import log_user_message, log_bot_response, log_conversation_exchange
from utils.response_parser import parse_yaml_response, validate_yaml_structure, parse_yaml_with_schema
from utils.prompts import (
    PROMPT_CLASSIFY_INPUT, 
    PROMPT_CLARIFYING_QUESTIONS_GENERIC,
    PROMPT_CLARIFYING_QUESTIONS_LOW_SCORE,
    PROMPT_COMPOSE_ANSWER,
    PROMPT_SUGGEST_FOLLOWUPS
)
from utils.helpers import (
    get_persona_for,
    get_topics_by_role,
    get_fallback_topics_by_role,
    get_intro_by_context,
    build_kb_context,
    build_history_text,
    classify_input_pattern,
    generate_clarifying_questions,
    get_context_for_input_type,
    get_context_for_knowledge_case,
    get_score_threshold
)
from typing import Any, Dict, List, Tuple
import textwrap
import yaml
import logging
import re

# Configure logging for this module
logger = logging.getLogger(__name__)


class AnswerNode(Node):
    def prep(self, shared):
        # Read question from shared
        return shared["question"]
    
    def exec(self, question):
        # Call LLM to get the answer
        return call_llm(question)
    
    def post(self, shared, prep_res, exec_res):
        # Store the answer in shared
        shared["answer"] = exec_res



# Removed _persona_for function - now imported from utils.helpers

# ========== Medical Agent Nodes ==========

class ClassifyInput(Node):
    """Node để phân loại input của user thành các loại khác nhau"""
    
    def prep(self, shared):
        logger.info("[ClassifyInput] PREP - Đọc query để phân loại")
        query = shared.get("query", "").strip()
        role = shared.get("role", "")
        logger.info(f"[ClassifyInput] PREP - Query: '{query}', Role: {role}")
        return query, role
    
    def exec(self, inputs):
        query, role = inputs
        
        # Quick pattern-based classification first
        pattern_result = classify_input_pattern(query)
        if pattern_result["confidence"] in ["high", "medium"]:
            logger.info(f"[ClassifyInput] EXEC - Pattern classification: {pattern_result}")
            return pattern_result
        
        # For ambiguous cases, use LLM
        if len(query) > 3:
            logger.info("[ClassifyInput] EXEC - Using LLM for classification")
            prompt = PROMPT_CLASSIFY_INPUT.format(query=query, role=role)
            
            try:
                resp = call_llm(prompt)
                result = parse_yaml_with_schema(
                    resp,
                    required_fields=["type"],
                    optional_fields=["confidence", "reason"],
                    field_types={"type": str, "confidence": str, "reason": str}
                )
                
                if result:
                    logger.info(f"[ClassifyInput] EXEC - LLM classification: {result}")
                    return result
            except Exception as e:
                logger.warning(f"[ClassifyInput] EXEC - LLM classification failed: {e}")
        
        # Default fallback
        logger.info(f"[ClassifyInput] EXEC - Default classification as statement: {query}")
        return {"type": "statement", "confidence": "low"}
    
    def post(self, shared, prep_res, exec_res):
        logger.info(f"[ClassifyInput] POST - Classification result: {exec_res}")
        shared["input_type"] = exec_res["type"]
        shared["classification_confidence"] = exec_res.get("confidence", "low")
        shared["classification_reason"] = exec_res.get("reason", "")
        
        # Return action based on classification
        return exec_res["type"]


class IngestQuery(Node):
    def prep(self, shared):
        logger.info("🔍 [IngestQuery] PREP - Đọc role và input từ shared")
        role = shared.get("role", "")
        user_input = shared.get("input", "")
        logger.info(f"🔍 [IngestQuery] PREP - Role: {role}, Input length: {len(user_input)}")
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


class RetrieveFromKB(Node):
    def prep(self, shared):
        logger.info("📚 [RetrieveFromKB] PREP - Đọc query để retrieve")
        query = shared.get("query", "")
        logger.info(f"📚 [RetrieveFromKB] PREP - Query: {query[:50]}...")
        return query

    def exec(self, query: str):
        logger.info("📚 [RetrieveFromKB] EXEC - Bắt đầu retrieve từ knowledge base")
        logger.info(f"📚 [RetrieveFromKB] EXEC - Query: {query}")
        results, score = retrieve(query, top_k=5)
        logger.info(f"📚 [RetrieveFromKB] EXEC - Retrieved {len(results)} results, best score: {score:.4f}")
        return results, score

    def post(self, shared, prep_res, exec_res):
        logger.info("📚 [RetrieveFromKB] POST - Lưu kết quả retrieve")
        results, score = exec_res
        shared["retrieved"] = results
        shared["retrieval_score"] = score
        shared["need_clarify"] = score < 0.15
        
        # Return action based on input type for flow routing
        input_type = shared.get("input_type", "medical_question")
        logger.info(f"📚 [RetrieveFromKB] POST - Saved {len(results)} results, score: {score:.4f}, routing to: {input_type}")
        return input_type


class ComposeAnswer(Node):
    def prep(self, shared):
        role = shared.get("role", "")
        query = shared.get("query", "")
        retrieved = shared.get("retrieved", [])
        need_clarify = shared.get("need_clarify", False)
        score = shared.get("retrieval_score", 0.0)
        history = shared.get("history", [])
        
        return (role, query, retrieved, need_clarify, score, history)

    def exec(self, inputs):
        role, query, hits, need_clarify, score, history = inputs
        persona = get_persona_for(role)

        # If query is very generic, ask the user to pick a subtopic first
        q_clean = (query or "").strip()
        is_generic = len(q_clean) <= 20 and len(q_clean.split()) <= 3
        logger.info(f"✍️ [ComposeAnswer] EXEC - Query analysis: is_generic={is_generic}, has_hits={len(hits) > 0}")
        
        if is_generic and hits:
            logger.info("✍️ [ComposeAnswer] EXEC - Tạo clarifying questions cho generic query")
            return generate_clarifying_questions(query, history, hits)

        if need_clarify or not hits:
            logger.info("✍️ [ComposeAnswer] EXEC - Tạo clarifying questions cho low score query")
            return generate_clarifying_questions(query, history)

        # Build context from KB hits
        ctx, sources, best_kb_answer = build_kb_context(hits)

        # Prepare formatting placeholders
        best_kb_summary = best_kb_answer or "[nội dung từ tư liệu]"
        kb_sources = sources or "- (Không có)"

        # Compose detailed answer
        prompt = PROMPT_COMPOSE_ANSWER.format(
            audience=persona['audience'],
            tone=persona['tone'],
            query=query,
            ctx=ctx,
            best_kb_answer=best_kb_answer,
            best_kb_summary=best_kb_summary,
            kb_sources=kb_sources
        )
        resp = call_llm(prompt)
        
        # Validate response before returning
        if not resp or not isinstance(resp, str):
            logger.warning("[ComposeAnswer] EXEC - Invalid LLM response, using fallback")
            resp = "Xin lỗi, tôi không thể tạo câu trả lời phù hợp lúc này. Vui lòng thử lại."
        
        return {"explain": "", "summary": "", "final": resp.strip(), "preformatted": True}

    # No fallback: rely entirely on LLM and let errors surface

    def post(self, shared, prep_res, exec_res):
        logger.info("✍️ [ComposeAnswer] POST - Lưu answer object")
        shared["answer_obj"] = exec_res
        shared["answer"] = exec_res.get("final", "")
        logger.info(f"✍️ [ComposeAnswer] POST - Answer keys: {list(exec_res.keys())}")
        logger.info(f"✍️ [ComposeAnswer] POST - Answer preview: {exec_res.get('final', '')[:100]}...")
        return "default"


class GreetingResponse(Node):
    """Node xử lý chào hỏi - set context và route đến topic suggestion"""
    
    def prep(self, shared):
        logger.info("[GreetingResponse] PREP - Set context cho greeting")
        return shared.get("role", "")
    
    def exec(self, role):
        logger.info("[GreetingResponse] EXEC - Set greeting context")
        return {"context_set": True, "role": role}
    
    def post(self, shared, prep_res, exec_res):
        logger.info("[GreetingResponse] POST - Set response_context = greeting")
        shared["response_context"] = "greeting"
        return "topic_suggest"


class StatementResponse(Node):
    """Node xử lý câu khẳng định - set context và route đến topic suggestion"""
    
    def prep(self, shared):
        logger.info("[StatementResponse] PREP - Set context cho statement")
        return shared.get("role", "")
    
    def exec(self, role):
        logger.info("[StatementResponse] EXEC - Set statement context")
        return {"context_set": True, "role": role}
    
    def post(self, shared, prep_res, exec_res):
        logger.info("[StatementResponse] POST - Set response_context = statement")
        shared["response_context"] = "statement"
        return "topic_suggest"


class NonsenseResponse(Node):
    """Node xử lý input không có nghĩa - set context và route đến topic suggestion"""
    
    def prep(self, shared):
        logger.info("[NonsenseResponse] PREP - Set context cho nonsense")
        return shared.get("role", "")
    
    def exec(self, role):
        logger.info("[NonsenseResponse] EXEC - Set nonsense context")
        return {"context_set": True, "role": role}
    
    def post(self, shared, prep_res, exec_res):
        logger.info("[NonsenseResponse] POST - Set response_context = nonsense")
        shared["response_context"] = "nonsense"
        return "topic_suggest"


class SuggestFollowups(Node):
    def prep(self, shared):
        return (
            shared.get("retrieved", []),
            shared.get("query", ""),
            shared.get("history", []),
            shared.get("answer", ""),
        )

    def exec(self, inputs):
        hits, query, history, answer_text = inputs
        
        # Build context
        ctx_lines = []
        for h in hits[:5]:
            ctx_lines.append(f"- {h['de_muc']} > {h['chu_de_con']} | Q: {h['cau_hoi']}")
        kb_ctx = "\n".join(ctx_lines)
        history_text = build_history_text(history)
        
        # Generate followup suggestions
        prompt = PROMPT_SUGGEST_FOLLOWUPS.format(
            query=query, answer_text=answer_text, history_text=history_text, kb_ctx=kb_ctx
        )
        resp = call_llm(prompt)
        
        # Use improved response parser with schema validation
        data = parse_yaml_with_schema(
            resp,
            required_fields=["questions"],
            field_types={"questions": list}
        )
        
        if data:
            questions = data.get("questions", [])
            # Additional validation: ensure questions are strings and non-empty
            valid_questions = [q for q in questions if isinstance(q, str) and q.strip()]
            
            if valid_questions:
                logger.info(f"[SuggestFollowups] EXEC - Successfully parsed {len(valid_questions)} questions")
                return valid_questions[:3]
            else:
                logger.warning("[SuggestFollowups] EXEC - No valid questions found in parsed data")
        else:
            logger.warning("[SuggestFollowups] EXEC - Failed to parse followup questions with schema validation")
        
        # Fallback: return empty list
        return []

    def post(self, shared, prep_res, exec_res):
        shared["suggestions"] = exec_res
        return "default"


class TopicSuggestResponse(Node):
    """Node xử lý gợi ý topic với template khác nhau cho từng context"""
    
    def prep(self, shared):
        role = shared.get("role", "")
        query = shared.get("query", "")
        retrieved = shared.get("retrieved", [])
        logger.info(f"[TopicSuggestResponse] content retrieve: {retrieved}")
        
        context = shared.get("response_context", "default")  # greeting, medical_low_score, statement, nonsense
        retrieval_score = shared.get("retrieval_score", 0.0)
        return role, query, retrieved, context, retrieval_score
    
    def exec(self, inputs):
        role, query, retrieved, context, retrieval_score = inputs
        persona = get_persona_for(role)
        
        logger.info(f"[TopicSuggestResponse] EXEC - Context: {context}, Role: {role}")
        
        # Retrieve topics từ KB dựa trên role
        role_based_topics = get_topics_by_role(role)
        
        if not role_based_topics:
            logger.warning(f"[TopicSuggestResponse] EXEC - No topics found for role: {role}, using fallback")
            role_based_topics = get_fallback_topics_by_role(role)
        
        # Tạo intro message dựa trên context
        intro_text = get_intro_by_context(context, role, query, retrieval_score, persona)
        
        # Format topic list
        topic_list = "\n".join([f"• {topic}" for topic in role_based_topics[:7]])
        final_answer = f"{intro_text}\n\n{topic_list}"
        
        return {
            "final": final_answer,
            "preformatted": True,
            "need_clarify": False,
            "topics": role_based_topics,
            "context": context
        }
    
    def post(self, shared, prep_res, exec_res):
        logger.info("[TopicSuggestResponse] POST - Lưu topic suggestion response")
        shared["answer_obj"] = exec_res
        shared["answer"] = exec_res.get("final", "")
        shared["suggestions"] = exec_res.get("topics", [])[:3]  # Lấy 3 đầu làm suggestions
        return "default"


class RetrievalDecisionNode(Node):
    """Node quyết định routing dựa trên retrieval score cho medical questions"""
    
    def prep(self, shared):
        logger.info("[RetrievalDecision] PREP - Kiểm tra retrieval score để quyết định routing")
        input_type = shared.get("input_type", "")
        retrieval_score = shared.get("retrieval_score", 0.0)
        query = shared.get("query", "")
        return input_type, retrieval_score, query
    
    def exec(self, inputs):
        input_type, retrieval_score, query = inputs
        
        logger.info(f"[RetrievalDecision] EXEC - Input type: {input_type}, Score: {retrieval_score:.4f}")
        
        # Threshold để quyết định có compose answer hay không
        score_threshold = 0.15
        
        if input_type == "medical_question":
            if retrieval_score >= score_threshold:
                logger.info(f"[RetrievalDecision] EXEC - Good score ({retrieval_score:.4f}), routing to compose")
                return {"action": "compose_answer", "score": retrieval_score}
            else: 
                logger.info(f"[RetrievalDecision] EXEC - Low score ({retrieval_score:.4f}), routing to topic suggestion")
                return {"action": "topic_suggest", "score": retrieval_score, "context": "medical_low_score"}
        elif input_type == "topic_suggestion":
            logger.info("[RetrievalDecision] EXEC - Topic suggestion request, routing to topic suggest")
            return {"action": "topic_suggest", "score": retrieval_score, "context": "topic_suggestion"}
        else:
            # Shouldn't happen trong flow này, nhưng fallback
            logger.warning(f"[RetrievalDecision] EXEC - Unexpected input type: {input_type}")
            return {"action": "topic_suggest", "score": retrieval_score, "context": "default"}
    
    def post(self, shared, prep_res, exec_res):
        logger.info(f"[RetrievalDecision] POST - Decision: {exec_res['action']}")
        
        # Set context cho TopicSuggestResponse nếu cần
        if "context" in exec_res:
            shared["response_context"] = exec_res["context"]
            
        return exec_res["action"]


class MainAgentNode(Node):
    """Main agent node để centralize tất cả logic quyết định"""
    
    def __init__(self, max_retries=1, wait=0):
        super().__init__(max_retries, wait)
        # Initialize sub-components
        self.classifier = ClassifyInput()
        self.retriever = RetrieveFromKB()
        self.composer = ComposeAnswer()
        self.topic_suggester = TopicSuggestResponse()
        self.followup_suggester = SuggestFollowups()
        
    def prep(self, shared):
        logger.info("[MainAgent] PREP - Đọc toàn bộ context")
        role = shared.get("role", "")
        query = shared.get("query", "")
        history = shared.get("history", [])
        return {"role": role, "query": query, "history": history}
    
    def exec(self, inputs):
        logger.info("[MainAgent] EXEC - Bắt đầu quy trình quyết định trung tâm")
        role = inputs["role"]
        query = inputs["query"]
        history = inputs["history"]
        
        # Step 1: Classify input with safety validation
        logger.info("[MainAgent] Step 1 - Classifying input")
        classify_prep = self.classifier.prep({"role": role, "query": query})
        classification = self.classifier.exec(classify_prep)
        
        # Validate classification result
        if not classification or not isinstance(classification, dict) or "type" not in classification:
            logger.error("[MainAgent] Invalid classification result, using fallback")
            classification = {"type": "statement", "confidence": "low"}
            
        input_type = classification["type"]
        confidence = classification.get("confidence", "medium")
        
        logger.info(f"[MainAgent] Classification: {input_type} (confidence: {confidence})")
        
        # Step 2: Handle based on classification
        if input_type in ["greeting", "statement", "nonsense"]:
            logger.info(f"[MainAgent] Handling {input_type} - routing to topic suggestions")
            return self._handle_simple_cases(input_type, role, query, history)
            
        elif input_type in ["medical_question", "topic_suggestion"]:
            logger.info(f"[MainAgent] Handling {input_type} - checking knowledge base")
            return self._handle_knowledge_cases(input_type, role, query, history)
            
        else:
            logger.warning(f"[MainAgent] Unknown input type: {input_type}, defaulting to topic suggestion")
            return self._handle_simple_cases("statement", role, query, history)
    
    def _handle_simple_cases(self, input_type, role, query, history):
        """Handle greeting, statement, nonsense cases - trả về topic suggestions"""
        logger.info(f"[MainAgent] _handle_simple_cases: {input_type}")
        
        # Set appropriate context
        context = get_context_for_input_type(input_type)
        
        # Generate topic suggestions with appropriate template
        topic_prep = self.topic_suggester.prep({
            "role": role,
            "query": query,
            "retrieved": [],
            "response_context": context,
            "retrieval_score": 0.0
        })
        topic_result = self.topic_suggester.exec(topic_prep)
        
        # Validate topic result
        if not topic_result or not isinstance(topic_result, dict):
            logger.error("[MainAgent] Invalid topic suggestion result, using fallback")
            topic_result = {"final": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.", "topics": []}
        
        return {
            "input_type": input_type,
            "context": context,
            "answer_obj": topic_result,
            "answer": topic_result.get("final", ""),
            "suggestions": topic_result.get("topics", [])[:3] if isinstance(topic_result.get("topics"), list) else [],
            "retrieval_score": 0.0,
            "retrieved": []
        }
    
    def _handle_knowledge_cases(self, input_type, role, query, history):
        """Handle medical_question, topic_suggestion cases - check KB first"""
        logger.info(f"[MainAgent] _handle_knowledge_cases: {input_type}")
        
        # Step 1: Retrieve from knowledge base
        retrieve_prep = self.retriever.prep({"query": query})
        retrieved, score = self.retriever.exec(retrieve_prep)
        
        logger.info(f"[MainAgent] Retrieved {len(retrieved)} results, score: {score:.4f}")
        
        # Step 2: Decide based on score and input type
        score_threshold = get_score_threshold()
        
        if input_type == "medical_question" and score >= score_threshold:
            logger.info("[MainAgent] Good retrieval score - composing detailed answer")
            return self._compose_detailed_answer(role, query, retrieved, score, history)
            
        else:
            # Low score medical question OR topic suggestion request
            context = get_context_for_knowledge_case(input_type)
            logger.info(f"[MainAgent] Low score or topic request - generating suggestions with context: {context}")
            return self._generate_topic_suggestions(input_type, context, role, query, retrieved, score)
    
    def _compose_detailed_answer(self, role, query, retrieved, score, history):
        """Compose detailed answer from KB with follow-up suggestions"""
        logger.info("[MainAgent] _compose_detailed_answer")
        
        # Compose main answer
        compose_prep = self.composer.prep({
            "role": role,
            "query": query, 
            "retrieved": retrieved,
            "need_clarify": False,
            "retrieval_score": score,
            "history": history
        })
        answer_result = self.composer.exec(compose_prep)
        
        # Validate answer result
        if not answer_result or not isinstance(answer_result, dict):
            logger.error("[MainAgent] Invalid compose answer result, using fallback")
            answer_result = {"final": "Xin lỗi, không thể tạo câu trả lời. Vui lòng thử lại."}
        
        # Generate follow-up suggestions
        followup_prep = self.followup_suggester.prep({
            "retrieved": retrieved,
            "query": query,
            "history": history,
            "answer": answer_result.get("final", "")
        })
        suggestions = self.followup_suggester.exec(followup_prep)
        
        # Validate suggestions
        if not isinstance(suggestions, list):
            logger.warning("[MainAgent] Invalid suggestions format, using empty list")
            suggestions = []
        
        return {
            "input_type": "medical_question",
            "context": "detailed_answer",
            "answer_obj": answer_result,
            "answer": answer_result.get("final", ""),
            "suggestions": suggestions[:3] if suggestions else [],
            "retrieval_score": score,
            "retrieved": retrieved
        }
    
    def _generate_topic_suggestions(self, input_type, context, role, query, retrieved, score):
        """Generate topic suggestions with appropriate context"""
        logger.info(f"[MainAgent] _generate_topic_suggestions: context={context}")
        
        topic_prep = self.topic_suggester.prep({
            "role": role,
            "query": query,
            "retrieved": retrieved,
            "response_context": context,
            "retrieval_score": score
        })
        topic_result = self.topic_suggester.exec(topic_prep)
        
        # Validate topic result
        if not topic_result or not isinstance(topic_result, dict):
            logger.error("[MainAgent] Invalid topic suggestion result in knowledge case, using fallback")
            topic_result = {"final": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.", "topics": []}
        
        return {
            "input_type": input_type,
            "context": context,
            "answer_obj": topic_result,
            "answer": topic_result.get("final", ""),
            "suggestions": topic_result.get("topics", [])[:3] if isinstance(topic_result.get("topics"), list) else [],
            "retrieval_score": score,
            "retrieved": retrieved
        }
    
    def post(self, shared, prep_res, exec_res):
        logger.info(f"[MainAgent] POST - Saving results: input_type={exec_res['input_type']}, context={exec_res['context']}")
        
        # Save all results to shared store
        shared["input_type"] = exec_res["input_type"]
        shared["response_context"] = exec_res["context"]
        shared["answer_obj"] = exec_res["answer_obj"]
        shared["answer"] = exec_res["answer"]
        shared["suggestions"] = exec_res["suggestions"]
        shared["retrieval_score"] = exec_res["retrieval_score"]
        shared["retrieved"] = exec_res["retrieved"]
        
        return "default"


class LogConversationNode(Node):
    """Node để log cuộc trò chuyện user-bot vào file"""
    
    def prep(self, shared):
        logger.info("[LogConversation] PREP - Chuẩn bị log conversation")
        user_query = shared.get("query", "")
        bot_answer = shared.get("answer", "")
        return user_query, bot_answer
    
    def exec(self, inputs):
        logger.info("[LogConversation] EXEC - Logging conversation to file")
        user_query, bot_answer = inputs
        
        # Log the complete exchange
        log_conversation_exchange(user_query, bot_answer)
        
        return {"logged": True, "user_query": user_query, "bot_answer": bot_answer}
    
    def post(self, shared, prep_res, exec_res):
        logger.info(f"[LogConversation] POST - Logged conversation: user='{exec_res['user_query'][:50]}...' bot='{exec_res['bot_answer'][:50]}...'")
        shared["conversation_logged"] = exec_res["logged"]
        return "default"
