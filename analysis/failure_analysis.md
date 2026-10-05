# Failure Analysis — Lab 18: Production RAG

**Họ và tên học viên:** Cao Đức Anh  
**Khóa:** K4 - Track 3B  

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | 0.5210 | 0.8650 | +0.3440 |
| Answer Relevancy | 0.5840 | 0.7920 | +0.2080 |
| Context Precision | 0.4500 | 0.8120 | +0.3620 |
| Context Recall | 0.5100 | 0.8400 | +0.3300 |

---

## Bottom-5 Failures

### #1
- **Question:** Thâm niên bao nhiêu năm thì được cộng thêm ngày phép?
- **Expected:** Theo chính sách v2024 hiện hành, nhân viên có thâm niên từ 3 năm trở lên được cộng thêm 1 ngày phép cho mỗi 3 năm. Chính sách cũ v2023 yêu cầu 5 năm.
- **Got:** Nhân viên có thâm niên 5 năm thì được cộng thêm 1 ngày phép theo quy định nghỉ phép của công ty.
- **Worst metric:** Faithfulness (hoặc Context Precision)
- **Error Tree:** Output sai → Context sai (lẫn văn bản cũ v2023) → Retrieval lấy nhầm chunk cũ do thiếu metadata filtering theo phiên bản văn bản.
- **Root cause:** Trong kho dữ liệu có cả 2 phiên bản văn bản v2023 và v2024. Tìm kiếm ngữ nghĩa thuần túy (Dense) bị thu hút bởi từ khóa tương tự nhưng không phân biệt được temporal metadata (ngày hiệu lực / phiên bản mới nhất).
- **Suggested fix:** Bổ sung metadata filtering trong M5 (`version: "v2024"`, `status: "effective"`) hoặc bổ sung temporal re-ranking ưu tiên văn bản có hiệu lực gần nhất.

### #2
- **Question:** Mật khẩu phải có tối thiểu bao nhiêu ký tự?
- **Expected:** Theo chính sách hiện hành (v2.0), mật khẩu phải có tối thiểu 12 ký tự. Chính sách cũ (v1.0) yêu cầu 8 ký tự nhưng đã bị thay thế.
- **Got:** Mật khẩu tối thiểu 8 ký tự.
- **Worst metric:** Faithfulness
- **Error Tree:** Output sai → Context bị nhiễu giữa v1.0 và v2.0 → Mô hình Reranker gán điểm cao cho cả 2 đoạn quy định mật khẩu nhưng LLM ưu tiên đọc đoạn đầu tiên.
- **Root cause:** Xung đột phiên bản chính sách nội bộ (Version Conflict).
- **Suggested fix:** Thêm quy tắc Prompt Engineering: *"Nếu tài liệu có nhiều phiên bản, chỉ sử dụng phiên bản có số hiệu cao nhất hoặc mới nhất"*.

### #3
- **Question:** Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT?
- **Expected:** Cần Giám đốc phòng ban (Director) phê duyệt. Cần xác nhận cấu hình kỹ thuật từ phòng CNTT trước khi đề xuất và đính kèm ít nhất 3 báo giá vì trên 10 triệu.
- **Got:** Cần Giám đốc phê duyệt và liên hệ CNTT để nhận máy. (Thiếu chi tiết 3 báo giá và xác nhận cấu hình).
- **Worst metric:** Context Recall
- **Error Tree:** Output thiếu ý → Context bị phân mảnh do thông tin về hạn mức tài chính và quy trình mua sắm CNTT nằm ở 2 văn bản khác nhau.
- **Root cause:** Multi-hop query: Một câu hỏi đòi hỏi thông tin từ Quy chế tài chính và Quy chế mua sắm thiết bị CNTT. Chunk size cố định không bao quát hết cả 2 nội dung.
- **Suggested fix:** Sử dụng Hierarchical chunking với parent chunk rộng hơn và tăng `top_k` của Hybrid search từ 20 lên 30 để gom đủ các chunks liên quan.

### #4
- **Question:** Mentor và buddy của nhân viên mới có thể là cùng một người không? Quản lý trực tiếp có thể làm mentor không?
- **Expected:** KHÔNG cho cả hai. Mentor và buddy phải là hai người khác nhau. Quản lý trực tiếp không được làm mentor hoặc buddy.
- **Got:** Không, mentor và buddy không được là cùng một người. (Bỏ sót vế quản lý trực tiếp).
- **Worst metric:** Answer Relevancy / Recall
- **Error Tree:** Output trả lời một nửa câu hỏi kép (compound question).
- **Root cause:** Query phức hợp gồm 2 câu hỏi con khiến LLM chỉ tập trung trả lời câu hỏi đầu tiên.
- **Suggested fix:** Áp dụng Query Decomposition ở bước tiền xử lý để tách câu hỏi kép thành 2 sub-queries độc lập trước khi search.

### #5
- **Question:** Nhân viên được tài trợ khóa học 25 triệu, nghỉ việc sau 8 tháng hoàn thành khóa học. Phải hoàn trả bao nhiêu?
- **Expected:** Phải hoàn trả 100% chi phí tức 25.000.000 VNĐ vì cam kết làm việc ít nhất 1 năm.
- **Got:** Nhân viên phải hoàn trả một phần chi phí đào tạo theo tỷ lệ thời gian cam kết còn lại.
- **Worst metric:** Faithfulness
- **Error Tree:** LLM hallucination / suy diễn dựa trên kiến thức chung thay vì bám sát chính xác điều khoản phạt 100% nếu nghỉ dưới 12 tháng.
- **Root cause:** Strict grounding chưa đủ mạnh, temperature mặc định cho phép LLM suy diễn theo luật lao động thông thường.
- **Suggested fix:** Thêm strict system prompt: *"CHỈ sử dụng công thức tính phạt được nêu rõ trong văn bản; không tự ý nội suy tỷ lệ nếu văn bản quy định hoàn trả 100%"*.

---

## Case Study (cho presentation)

**Question chọn phân tích:**  
*"Thâm niên bao nhiêu năm thì được cộng thêm ngày phép?"*

**Error Tree walkthrough:**
1. **Output đúng?** $\rightarrow$ **SAI**. Trả lời 5 năm (chính sách v2023) thay vì 3 năm (chính sách hiện hành v2024).
2. **Context đúng?** $\rightarrow$ **LẪN LỘN**. Cả 2 chunk từ `Quy_che_nghi_phep_v2023.txt` và `Quy_che_nghi_phep_v2024.txt` đều được retrieved vào top context do độ tương đồng từ khóa quá cao.
3. **Query rewrite OK?** $\rightarrow$ Query ban đầu ngắn, không chỉ định rõ thời điểm tra cứu ("năm 2024" hay "hiện tại").
4. **Fix ở bước:** 
   - **M5 (Enrichment):** Trích xuất metadata `version` và `effective_date`.
   - **M2 (Search):** Thêm bộ lọc metadata `is_latest: true`.
   - **Prompt Generation:** Bổ sung chỉ dẫn ưu tiên phiên bản mới nhất.

**Nếu có thêm 1 giờ, sẽ optimize:**
- Triển khai **Query Decomposition** và **HyDE (Hypothetical Document Embeddings)** để giải quyết dứt điểm các câu hỏi so sánh đa văn bản và multi-hop questions.
- Thêm cơ chế **Self-Correction (Agentic RAG / CRAG)** để kiểm định tính mâu thuẫn giữa các tài liệu cũ và mới trước khi sinh câu trả lời cuối cùng.
