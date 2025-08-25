"""
Helper functions for medical agent nodes
"""

from typing import Dict, List, Tuple, Any
import logging
import re
import yaml
from .call_llm import call_llm
from .kb import retrieve_random_by_role
from .response_parser import parse_yaml_response, validate_yaml_structure

logger = logging.getLogger(__name__)


def get_persona_for(role: str) -> Dict[str, str]:
    """Get persona configuration based on user role"""
    rl = role.lower()
    if "bác sĩ nha khoa" in rl:
        return {
            "persona": "Bác sĩ nội tiết (chuyên ĐTĐ)",
            "audience": "bác sĩ nha khoa",
            "tone": (
                "Giải thích ngắn gọn, chính xác, nhấn mạnh liên hệ kiểm soát đường huyết với chăm sóc nha chu,"
                " khuyến cáo phối hợp lâm sàng rõ ràng."
            ),
        }
    if "bác sĩ nội tiết" in rl:
        return {
            "persona": "Bác sĩ nha khoa (ưu tiên nha chu)",
            "audience": "bác sĩ nội tiết",
            "tone": (
                "Tập trung biến chứng răng miệng ảnh hưởng kiểm soát đường huyết,"
                " trình bày quy trình điều trị nha khoa an toàn cho ĐTĐ."
            ),
        }
    if "bệnh nhân đái tháo đường" in rl or "đái tháo đường" in rl:
        return {
            "persona": "Bác sĩ nội tiết",
            "audience": "bệnh nhân",
            "tone": (
                "Ngôn ngữ giản dị, thực hành, an toàn; đưa bước cụ thể và khi nào cần khám nha khoa."
            ),
        }
    # Bệnh nhân nha khoa (mặc định)
    return {
        "persona": "Bác sĩ nha khoa",
        "audience": "bệnh nhân",
        "tone": (
            "Ngôn ngữ thân thiện, chú trọng chăm sóc răng miệng hằng ngày và cảnh báo khi cần kiểm tra đường huyết."
        ),
    }


def get_topics_by_role(role: str) -> Tuple[List[str], str]:
    """Retrieve topics from KB based on user role - returns topics and intro"""
    try:
        # Retrieve ngẫu nhiên từ CSV file tương ứng với role
        results = retrieve_random_by_role(role, count=7)
        
        if results:
            topics = []
            for item in results:
                # Sử dụng câu hỏi làm topic
                topic = item.get('cau_hoi', '').strip()
                if topic and len(topic) > 10:  # Lọc câu hỏi có ý nghĩa
                    topics.append(topic)
            
            # Tạo intro phù hợp với role
            persona = get_persona_for(role)
            intro = f"Dưới đây là một số chủ đề phù hợp với {persona['audience']} từ cơ sở tri thức:"
            
            return topics[:7]
        else:
            return [], ""
            
    except Exception as e:
        logger.warning(f"Failed to retrieve random topics for role '{role}': {e}")
        return [], ""


def get_fallback_topics_by_role(role: str) -> List[str]:
    """Fallback topics based on role when cannot retrieve from KB"""
    role_lower = role.lower()
    
    if "bác sĩ nha khoa" in role_lower:
        return [
            "Quản lý bệnh nhân đái tháo đường trong nha khoa",
            "Điều trị viêm nha chu ở bệnh nhân ĐTĐ",
            "Phối hợp với bác sĩ nội tiết trong điều trị",
            "Biến chứng nha khoa do đái tháo đường",
            "Kháng sinh trong điều trị nha khoa bệnh nhân ĐTĐ"
        ]
    elif "bác sĩ nội tiết" in role_lower:
        return [
            "Mối liên hệ giữa kiểm soát đường huyết và sức khỏe nha chu",
            "Khi nào giới thiệu bệnh nhân đến nha khoa",
            "Thuốc đái tháo đường ảnh hưởng đến răng miệng",
            "Biến chứng răng miệng ở bệnh nhân ĐTĐ type 1 và type 2",
            "Tư vấn chăm sóc răng miệng cho bệnh nhân ĐTĐ"
        ]
    elif "đái tháo đường" in role_lower:
        return [
            "Cách chăm sóc răng miệng khi bị đái tháo đường",
            "Triệu chứng cảnh báo ở răng miệng cần chú ý",
            "Khi nào cần đi khám nha khoa",
            "Chế độ ăn tốt cho răng miệng và đường huyết",
            "Cách đánh răng đúng cách cho người ĐTĐ"
        ]
    else:
        # Default cho bệnh nhân nha khoa hoặc không xác định
        return [
            "Cách chăm sóc răng miệng hàng ngày",
            "Dấu hiệu cần khám nha khoa ngay",
            "Phòng ngừa sâu răng và viêm nướu",
            "Chế độ ăn uống tốt cho răng miệng",
            "Tần suất khám nha khoa định kỳ"
        ]


def get_intro_by_context(context: str, role: str, query: str, retrieval_score: float, persona: Dict[str, str]) -> str:
    """Generate intro message based on context and role"""
    audience = persona.get("audience", "người dùng")
    
    if context == "greeting":
        return f"Xin chào! Tôi là ai agent hỗ trợ tư vấn y khoa.\n\nTôi có thể giúp bạn tư vấn về các chủ đề sau:"
        
    elif context == "medical_low_score":
        return f"Tôi hiểu câu hỏi của bạn, nhưng không tìm thấy thông tin cụ thể trong cơ sở tri thức (điểm tương đồng: {retrieval_score:.2f}).\n\nTôi gợi ý một số chủ đề liên quan phù hợp với {audience}:"
        
    elif context == "statement":
        return f"Cảm ơn bạn đã chia sẻ thông tin. Để tôi có thể hỗ trợ tốt hơn, bạn có muốn tìm hiểu về các chủ đề sau không:"
        
    elif context == "nonsense":
        return f"Xin lỗi, tôi không hiểu ý bạn. Bạn có thể đặt câu hỏi rõ ràng hơn về các chủ đề sau:"
        
    elif context == "topic_suggestion":
        return f"Dưới đây là những chủ đề phù hợp với {audience} từ cơ sở tri thức:"
        
    else:  # default
        return f"Dưới đây là một số chủ đề bạn có thể quan tâm:"


def build_kb_context(hits: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """Build context from KB hits - returns ctx, sources, best_kb_answer"""
    ctx_lines: List[str] = []
    src_lines: List[str] = []
    best_kb_answer = ""
    
    if hits:
        best_kb_answer = hits[0].get('cau_tra_loi', '')
        
    for h in hits[:3]:
        ctx_lines.append(
            f"- [{h['ma_so']}] {h['de_muc']} > {h['chu_de_con']} | Q: {h['cau_hoi']} | A: {h['cau_tra_loi']}"
        )
        src_lines.append(f"- [{h['ma_so']}] {h['de_muc']} > {h['chu_de_con']}")
    
    ctx = "\n".join(ctx_lines)
    sources = "\n".join(src_lines)
    
    return ctx, sources, best_kb_answer


def build_history_text(history: List[Dict[str, str]]) -> str:
    """Format conversation history for prompts"""
    return "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history[-6:]])


def classify_input_pattern(query: str) -> Dict[str, str]:
    """Quick pattern-based classification for common cases"""
    query_lower = query.lower()
    
    # Greeting patterns
    greeting_patterns = [
        r'^(hi|hello|chào|xin chào|chào bạn|hey)$',
        r'^(hi|hello|chào|xin chào|chào bạn|hey)\s*[!.]*$',
        r'^(tôi|mình)\s+(là|tên)\s+.+$',  # "tôi là..."
    ]
    
    for pattern in greeting_patterns:
        if re.match(pattern, query_lower):
            return {"type": "greeting", "confidence": "high"}
    
    # Nonsense patterns (very short, no meaning)
    if len(query) <= 2 and not re.match(r'^[a-zA-Zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]+$', query):
        return {"type": "nonsense", "confidence": "high"}
    
    # Topic suggestion patterns
    topic_suggestion_patterns = [
        r'gợi ý.*?(topic|chủ đề|vấn đề|câu hỏi|nội dung)',
        r'(liệt kê|cho.*danh sách|danh sách.*gì)',
        r'có những.*(topic|chủ đề|vấn đề|câu hỏi)',
        r'(tôi|mình).*(nên hỏi|có thể hỏi).*gì',
        r'gợi ý.*(vài|một số|mấy)',
        r'topic.*?(gì|nào|nào hay)',
    ]
    
    for pattern in topic_suggestion_patterns:
        if re.search(pattern, query_lower):
            return {"type": "topic_suggestion", "confidence": "high"}
    
    # Medical question patterns
    medical_keywords = [
        'đau', 'bệnh', 'điều trị', 'thuốc', 'răng', 'nha khoa', 'tiểu đường', 'đái tháo đường',
        'nội tiết', 'insulin', 'glucose', 'đường huyết', 'viêm', 'sưng', 'nhức', 'chữa',
        'khám', 'bác sĩ', 'tư vấn', 'triệu chứng', 'chẩn đoán'
    ]
    
    has_medical_keyword = any(keyword in query_lower for keyword in medical_keywords)
    has_question_word = any(word in query_lower for word in ['sao', 'như thế nào', 'làm thế nào', 'tại sao', 'có nên', 'có thể', '?'])
    
    if has_medical_keyword or has_question_word:
        return {"type": "medical_question", "confidence": "medium"}
    
    return {"type": "statement", "confidence": "low"}


def generate_clarifying_questions(query: str, history: List[Dict[str, str]], hits: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate clarifying questions for generic or low-score queries"""
    from .prompts import PROMPT_CLARIFYING_QUESTIONS_GENERIC, PROMPT_CLARIFYING_QUESTIONS_LOW_SCORE
    
    history_text = build_history_text(history)
    
    if hits:
        # Generic query with KB hits
        ctx_lines = []
        for h in hits[:5]:
            ctx_lines.append(f"- {h['de_muc']} > {h['chu_de_con']} | Q: {h['cau_hoi']}")
        kb_ctx = "\n".join(ctx_lines)
        
        prompt = PROMPT_CLARIFYING_QUESTIONS_GENERIC.format(
            query=query, history_text=history_text, kb_ctx=kb_ctx
        )
    else:
        # Low score query without hits
        prompt = PROMPT_CLARIFYING_QUESTIONS_LOW_SCORE.format(
            query=query, history_text=history_text
        )
    
    try:
        resp = call_llm(prompt)
        data = parse_yaml_response(resp)
        
        if data and validate_yaml_structure(data, required_fields=["questions"]):
            qs = [q for q in data.get("questions", []) if isinstance(q, str) and q.strip()]
            if len(qs) < 2:
                raise ValueError("Not enough questions")
            lead = data.get("lead", "Bạn quan tâm đến nội dung nào?")
            return {
                "explain": "",
                "summary": "",
                "final": lead,
                "clarify_questions": qs[:5],
                "need_clarify": True,
                "ask_first_title": lead,
                "preformatted": False,
            }
    except Exception as e:
        logger.warning(f"Failed to parse clarifying questions: {e}")
    
    # Fallback
    lead = "Bạn quan tâm đến nội dung nào?"
    return {
        "explain": "",
        "summary": "",
        "final": lead,
        "clarify_questions": [],
        "need_clarify": True,
        "ask_first_title": lead,
        "preformatted": False,
    }


def get_context_for_input_type(input_type: str) -> str:
    """Get appropriate context for input type"""
    context_map = {
        "greeting": "greeting",
        "statement": "statement", 
        "nonsense": "nonsense"
    }
    return context_map.get(input_type, "statement")


def get_context_for_knowledge_case(input_type: str) -> str:
    """Get context for knowledge-based cases"""
    if input_type == "medical_question":
        return "medical_low_score"
    else:
        return "topic_suggestion"


def get_score_threshold() -> float:
    """Get retrieval score threshold for decision making"""
    return 0.15
