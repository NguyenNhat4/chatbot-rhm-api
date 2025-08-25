"""
Prompts for medical agent nodes
"""

PROMPT_CLASSIFY_INPUT = """
Phân loại câu sau của user trong ứng dụng tư vấn y khoa:

Input: "{query}"
Role context: {role}

Phân loại thành một trong các loại sau:
1. greeting - chào hỏi, giới thiệu
2. medical_question - câu hỏi y khoa, sức khỏe cụ thể
3. topic_suggestion - yêu cầu gợi ý topic, chủ đề, danh sách câu hỏi
4. statement - câu khẳng định, chia sẻ thông tin
5. nonsense - không có nghĩa, spam

Trả lời đúng format YAML sau:
```yaml
type: <loại>
confidence: <high/medium/low>
reason: <lý do ngắn gọn>
```"""

PROMPT_CLARIFYING_QUESTIONS_GENERIC = """
Bạn là trợ lý y khoa. Người dùng đang hỏi khá chung: '{query}'.
Dưới đây là bối cảnh hội thoại gần đây:
{history_text}

Và một số câu hỏi liên quan trong cơ sở tri thức:
{kb_ctx}

Hãy đề xuất 3-5 câu hỏi gợi ý CỤ THỂ, tự nhiên, không trùng lặp, giúp thu hẹp phạm vi.
Xuất kết quả ở YAML:

```yaml
lead: |
  Câu hỏi của bạn đang khá rộng. Mình gợi ý một số nội dung để bạn chọn:
questions:
  - ...
  - ...
```"""

PROMPT_CLARIFYING_QUESTIONS_LOW_SCORE = """
Bạn là trợ lý y khoa. Người dùng hỏi: '{query}'.
Bối cảnh gần đây:
{history_text}

Hãy đưa 3-5 câu hỏi gợi ý cần thiết để làm rõ và thu hẹp phạm vi.
Hãy ưu tiên các khía cạnh an toàn và thông tin lâm sàng thiết yếu.
Xuất kết quả ở YAML:

```yaml
lead: |
  Câu hỏi của bạn đang khá chung. Bạn quan tâm đến nội dung nào?
questions:
  - ...
  - ...
```"""

PROMPT_COMPOSE_ANSWER = """
Bạn là người cung cấp tri thức y khoa dựa trên cơ sở dữ liệu (không tư vấn điều trị cá nhân).
Đối tượng: {audience}. Giọng điệu: {tone}.
Phong cách viết: tự nhiên, chuyên nghiệp, mạch lạc, câu dài-ngắn xen kẽ; tránh lặp từ;
không sử dụng các cụm như 'theo tri thức' hay 'ngữ cảnh' trong câu trả lời;
không đặt dấu ngoặc kép quanh câu hỏi gợi ý.
Nếu câu hỏi đòi chẩn đoán/điều trị cụ thể, hãy khuyến khích người dùng hỏi bác sĩ điều trị.

Câu hỏi: {query}

Tư liệu trích từ cơ sở tri thức:
{ctx}

Câu trả lời trực tiếp từ cơ sở tri thức (để sử dụng cho tóm tắt): {best_kb_answer}

Xuất kết quả bằng tiếng Việt, định dạng Markdown, theo cấu trúc sau:
### Diễn giải
- Viết liền mạch, bám sát nội dung tư liệu.

### Tóm tắt
👉Tóm lại là {best_kb_summary}

### Gợi ý câu hỏi
- 2–3 câu hỏi liên quan (ưu tiên lấy trực tiếp từ tư liệu hoặc để làm rõ).

### Nguồn tri thức
{kb_sources}"""

PROMPT_SUGGEST_FOLLOWUPS = """
Dựa trên câu hỏi ban đầu: '{query}', câu trả lời:'''{answer_text}''',
bối cảnh gần đây:
{history_text}

và các mục liên quan truy xuất bằng vector từ cơ sở tri thức:
{kb_ctx}

Hãy đề xuất 2-3 câu hỏi tiếp theo ngắn gọn, hữu ích để người dùng đào sâu.
Xuất YAML:

```yaml
questions:
  - ...
  - ...
```"""
