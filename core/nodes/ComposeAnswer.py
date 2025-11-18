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


class ComposeAnswer(Node):
    def prep(self, shared):
        # Import dependencies
        from utils.knowledge_base.qdrant_retrieval import get_full_qa_by_ids
        from utils.role_enum import RoleEnum

        # Role to collection mapping
        ROLE_TO_COLLECTION = {
            RoleEnum.PATIENT_DIABETES.value: "bndtd",
            RoleEnum.DOCTOR_ENDOCRINE.value: "bsnt",
            RoleEnum.PATIENT_DENTAL.value: "bnrhm",
            RoleEnum.DOCTOR_DENTAL.value: "bsrhm",
        }
        context_summary = shared.get("context_summary", "")
        role = shared.get("role", "")
        query = shared.get("retrieval_query", "query").strip()

        selected_ids = shared.get("selected_ids", [])
        # Map role to collection name
        collection_name = ROLE_TO_COLLECTION.get(role, "bnrhm")

        logger.info(f"✍️ [ComposeAnswer] PREP - Role: '{role}' -> Collection: '{collection_name}', Query: '{query[:50]}...', Selected IDs: {selected_ids}")

        # Fetch full QA data from Qdrant using IDs
        if selected_ids:
            retrieved_qa = get_full_qa_by_ids(selected_ids, collection_name=collection_name)
            logger.info(f"✍️ [ComposeAnswer] PREP - Retrieved {len(retrieved_qa)} full QA pairs from Qdrant")
        else:
            logger.warning("✍️ [ComposeAnswer] PREP - No selected IDs, using empty list")
            retrieved_qa = []

        return role, query, retrieved_qa,context_summary

    def exec(self, inputs):
        # Import dependencies only when needed
        import time
        from utils.role_enum import PERSONA_BY_ROLE
        from utils.helpers import format_kb_qa_list
        from utils.llm import call_llm
        from utils.parsing import parse_yaml_with_schema
        from utils.auth import APIOverloadException
        from config.timeout_config import timeout_config

        role, query, retrieved, context_summary = inputs

        # Handle missing or invalid role with fallback
        if role not in PERSONA_BY_ROLE:
            logger.warning(f"✍️ [ComposeAnswer] EXEC - Invalid role '{role}', using default patient_diabetes role")
            role = "patient_diabetes"  # Default fallback role

        persona = PERSONA_BY_ROLE[role]
        # Compact KB context
        relevant_info_from_kb = format_kb_qa_list(retrieved, max_items=6)

        prompt = f"""
Hay cung cấp tri thức y khoa dựa trên cơ sở tri thức do bác sĩ biên soạn.
Bối cảnh hội thoại : {context_summary}
User là :{ persona["audience"] }
Câu hỏi cần trả lời: {query}

Danh sách Q&A đã retrieve:
{relevant_info_from_kb}

Lưu ý:
1) -   Không chào, đi thẳng vào câu trả lời,không tự trả lời nếu Q&A rỗng hoặc không đủ thông tin.
  - { persona["tone"]}.
   - Kết thúc bằng một dòng tóm lược bắt đầu bằng “👉 Tóm lại,”.
2) `suggestion_questions` là danh sách các câu hỏi gợi hướng tiếp theo cho người dùng.

```yaml
explanation: |
  <câu trả lời của bạn dựa trên thông tin Q&A;  dùng **nhấn mạnh** cho các từ khoá quan trọng>
  👉 Tóm lại, <tóm lược ngắn gọn có thể dựa vào danh sách Q&A>
suggestion_questions: |
  - "Câu hỏi gợi ý 1"
  - "Câu hỏi gợi ý 2"
  - "Câu hỏi gợi ý 3"
```

Trả về chính xác cấu trúc yaml như ở trên trên:
"""
        logger.info(f"✍️ [ComposeAnswer] EXEC - prompt: {prompt}")

        try:
            result = call_llm(prompt, max_retry_time=1)
            # Log LLM timing
            logger.info(f"✍️ [ComposeAnswer] EXEC - LLM response received")
            result = parse_yaml_with_schema(result, required_fields=["explanation", "suggestion_questions"], field_types={"explanation": str, "suggestion_questions": list})
            logger.info(f"✍️ [ComposeAnswer] EXEC - result: {result}")

            if not result or  isinstance(result, str):
                logger.warning("[ComposeAnswer] EXEC - Invalid LLM response, using fallback")
                resp = "Xin lỗi, tôi không thể tạo câu trả lời phù hợp lúc này. Bạn đặt câu hỏi khác được không? "
                return {"explain": resp, "suggestion_questions": [], "preformatted": True}

            return {"explain": result.get("explanation", ""), "suggestion_questions": result.get("suggestion_questions", []), "preformatted": True}

        except APIOverloadException as e:
            logger.warning(f"✍️ [ComposeAnswer] EXEC - API overloaded, triggering fallback mode: {e}")
            # Return flag to indicate API overload - will be handled in post method
            resp = "API hiện đang quá tải, đang chuyển sang chế độ fallback..."
            return {"explain": resp, "suggestion_questions": [], "preformatted": True, "api_overload": True}


    def post(self, shared, prep_res, exec_res):
        logger.info("✍️ [ComposeAnswer] POST - Lưu answer object")
        shared["answer_obj"] = exec_res
        shared["explain"] = exec_res.get("explain", "")
        shared["suggestion_questions"] = exec_res.get("suggestion_questions", [])
        logger.info(f"✍️ [ComposeAnswer] POST - Answer keys: {list(exec_res.keys())}")
        logger.info(f"✍️ [ComposeAnswer] POST - Answer preview: {exec_res.get('explain')}")
        
        # Check if API overload occurred and route to fallback
        if exec_res.get("api_overload", False):
            logger.info("✍️ [ComposeAnswer] POST - API overloaded, routing to fallback")
            return "fallback"
        
        return "default"
