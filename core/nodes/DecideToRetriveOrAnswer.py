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


class DecideToRetriveOrAnswer(Node):
    """Main decision agent - ONLY decides between RAG agent or chitchat agent"""

    def prep(self, shared):
        logger.info("[MainDecision] PREP - Đọc query để phân loại RAG vs chitchat")
        query = shared.get("query", "").strip()
        role = shared.get("role", "")
        conversation_history = shared.get("conversation_history", [])
        # Lấy 3 cặp gần nhất (6 tin)
        history_lines = []
        for msg in conversation_history[-6:]:
            try:
                who = msg.get("role")
                content = msg.get("content", "")
                history_lines.append(f"- {who}: {content}")
            except Exception:
                continue
        formatted_history = "\n".join(history_lines)
        return query, role, formatted_history

    def exec(self, inputs):
        # Import dependencies only when needed
        from utils.llm import call_llm
        from utils.parsing import parse_yaml_with_schema
        from utils.auth import APIOverloadException
        from config.timeout_config import timeout_config

        query, role, formatted_history = inputs
        logger.info("[MainDecision] EXEC - Deciding and responding")

        # Prompt: decide type AND generate response if direct_response
        prompt = f"""Bạn là trợ lý y tế nha khoa và nội tiết. Phân tích câu hỏi và quyết định.

Câu hỏi: "{query}"

Hành động:
- direct_response: trao đổi xuồng sả.  
- retrieve_kb: câu hỏi về y tế cần tra kiến thức y tế. 

Trả về YAML:
```yaml
type: direct_response
explanation: "Câu trả lời của bạn ở đây"
```

HOẶC nếu cần tra KB:
```yaml
type: retrieve_kb
explanation: ""
```"""

        try:
            resp = call_llm(prompt, fast_mode=True, max_retry_time=timeout_config.LLM_RETRY_TIMEOUT)

            result = parse_yaml_with_schema(
                resp,
                required_fields=["type"],
                optional_fields=["explanation"],
                field_types={"type": str, "explanation": str}
            )

            decision_type = result.get("type", "")
            explanation = result.get("explanation", "")

            logger.info(f"[MainDecision] EXEC - Type: {decision_type}, Explanation length: {len(explanation)}")

            return {"type": decision_type, "explanation": explanation}

        except APIOverloadException as e:
            logger.warning(f"[MainDecision] EXEC - API overloaded, triggering fallback: {e}")
            return {"type": "api_overload", "explanation": ""}
        except Exception as e:
            logger.warning(f"[MainDecision] EXEC - LLM classification failed: {e}")
            return {"type": "default", "explanation": ""}

    def post(self, shared, prep_res, exec_res):
        logger.info(f"[MainDecision] POST - Classification result: {exec_res}")
        input_type = exec_res.get("type", "")
        explanation = exec_res.get("explanation", "")

        # Save explanation to shared if direct_response
        if input_type == "direct_response" and explanation:
            shared["answer_obj"] = {
                "explain": explanation,
                "preformatted": True,
                "suggestion_questions": []
            }
            shared["explain"] = explanation
            shared["suggestion_questions"] = []
            logger.info(f"[MainDecision] POST - Direct response saved to 'explain': {explanation[:80]}...")
            return "direct_response"
        elif input_type == "retrieve_kb":
            # Initialize retrieve attempts counter for RAG pipeline
            shared["retrieve_attempts"] = 0
            logger.info("[MainDecision] POST - Complex question, routing to retrieve_kb (attempts=0)")
            return "retrieve_kb"
        elif input_type == "api_overload" or input_type == "default":
            logger.warning("[MainDecision] POST - API issue, routing to fallback")
            return "fallback"
        else:
            # Fallback: if unknown type or no explanation, route to fallback
            logger.warning(f"[MainDecision] POST - Unknown type '{input_type}', routing to fallback")
            return "fallback"
