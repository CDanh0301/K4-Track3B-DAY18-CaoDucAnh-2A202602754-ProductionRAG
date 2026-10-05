# Individual Reflection — Lab 18: Production RAG

**Họ và tên:** Cao Đức Anh  
**Khóa:** K4 - Track 3B  
**Ngày hoàn thành:** 05/10/2026

---

## Phần 1: Mapping bài giảng (Lecture Mapping)
Map từng concept trong lecture vào code cụ thể trong lab:

| Lecture Concept | Module | Hàm cụ thể | Observation & Phân tích |
|----------------|--------|-------------|--------------------------|
| Semantic chunking | M1 | `chunk_semantic()` | Sử dụng Cosine Similarity giữa câu liên tiếp (threshold 0.85); gom các câu có ngữ nghĩa tương đồng vào cùng 1 chunk, khắc phục nhược điểm cắt đôi ý câu của fixed-size chunking. |
| BM25 + Dense fusion | M2 | `reciprocal_rank_fusion()` | Áp dụng công thức RRF $RRF\_score(d) = \sum \frac{1}{k + rank(d)}$ với $k=60$. Cân bằng xuất sắc giữa từ khóa chính xác (BM25 với underthesea tokenizer) và ngữ nghĩa sâu (Dense Qdrant với model `bge-m3`). |
| Cross-encoder reranking | M3 | `CrossEncoderReranker.rerank()` | Sử dụng mô hình `BAAI/bge-reranker-v2-m3` để chấm điểm tương tác chéo query-document từ top-20 candidate xuống top-3/5, tăng đáng kể precision cho bước generation. Áp dụng Singleton pattern để cache model trong bộ nhớ. |
| RAGAS 4 metrics | M4 | `evaluate_ragas()` | Đánh giá 4 chỉ số cốt lõi: Faithfulness, Answer Relevancy, Context Precision, Context Recall. Cấu hình Concurrency Control và Retry qua `RunConfig` để xử lý Rate Limit từ LLM provider. |
| Contextual embeddings & Enrichment | M5 | `contextual_prepend()` / `_enrich_single_call()` | Bổ sung ngữ cảnh xuất xứ tài liệu và tóm tắt vào trước từng chunk giúp giải quyết triệt để vấn đề mất ngữ cảnh khi chunking; tối ưu hóa chi phí với Combined Single-Call mode (1 API call trả về cả Summary, HyQA, Context, Auto Metadata). |

---

## Phần 2: Khó khăn & Cách giải quyết (Challenges & Debugging)

- **Lỗi kỹ thuật gặp phải (Exact error message):**
  - `Error code: 429 - Rate limit reached for gpt-4o-mini on requests per day (RPD): Limit 10000, Used 10000`
  - `TimeoutError()` khi Ragas chạy song song nhiều worker với độ trễ mạng quốc tế.
- **Nguyên nhân gốc rễ & Cách debug:**
  - *Nguyên nhân:* Mặc định thư viện Ragas chạy với `max_workers=16` và timeout dài, dẫn đến bùng nổ request vượt ngưỡng TPM/RPD của tài khoản OpenAI. Khi mạng chập chờn, client rơi vào vòng lặp retry vô tận làm nghẽn toàn bộ pipeline.
  - *Cách debug & xử lý:*
    1. Cấu hình tường minh `RunConfig` trong `m4_eval.py` với `max_workers=8`, `timeout=30s`, `max_retries=2` để fail-fast và retry linh hoạt.
    2. Trong `pipeline.py` và `m5_enrichment.py`, bổ sung fallback tự động khi LLM generation thất bại (fallback lấy context trích xuất tốt nhất), đảm bảo pipeline chạy end-to-end an toàn.
- **Kiến thức còn thiếu & Cách khắc phục:**
  - Hiểu sâu hơn về Rate Limiting (TPM, RPM, RPD) và cơ chế concurrency control khi triển khai Production RAG. Cần áp dụng batching và local caching cho embedding/enrichment thay vì gọi API trực tiếp từng phần tử.

---

## Phần 3: Action Plan cho Project cá nhân (Application Plan)

### Project: Hệ thống Trợ lý Pháp lý & Tra cứu Quy chế Doanh nghiệp

#### 1. Hiện trạng
- **Pipeline hiện tại:** Sử dụng Basic RAG (cắt đoạn thô theo ký tự 500 chars, dense search với OpenAI text-embedding-ada-002, LLM trả lời trực tiếp).
- **Vấn đề / Bottlenecks đang gặp:**
  - Tỷ lệ hallucination cao do chunk bị đứt đoạn giữa các điều khoản luật.
  - Từ khóa pháp lý chính xác (số hiệu thông tư, nghị định) bị dense search bỏ sót.
  - Không có cơ chế đo lường định lượng chất lượng câu trả lời.

#### 2. Kế hoạch cải tiến
1. **Chunking strategy:** Áp dụng Structure-aware Chunking theo Điều/Khoản luật và Hierarchical Chunking (Parent chunk chứa toàn bộ Điều, Child chunk chứa từng Khoản).
2. **Search retrieval:** Triển khai Hybrid Search kết hợp BM25 (token hóa tiếng Việt chuyên dụng) và Dense Vector qua Reciprocal Rank Fusion (RRF).
3. **Reranking:** Tích hợp Cross-Encoder `bge-reranker-v2-m3` để chọn lọc top 3 đoạn quy chế liên quan nhất trước khi đưa vào LLM context.
4. **Evaluation:** Thiết lập bộ benchmark tự động bằng Ragas với 4 metrics (đặc biệt theo dõi chặt chẽ Faithfulness $\ge 0.85$ để triệt tiêu bịa đặt pháp lý).
5. **Enrichment:** Áp dụng Contextual Prepend (gắn số hiệu văn bản, ngày ban hành vào đầu mỗi chunk) và Metadata Extraction để lọc theo ngày hiệu lực.

#### 3. Timeline triển khai
- **Tuần 1:** Tái cấu trúc pipeline dữ liệu văn bản: triển khai Structure-aware chunking và Hybrid Search (BM25 + Dense Qdrant).
- **Tuần 2:** Tích hợp Cross-Encoder reranker, xây dựng bộ test Ragas 50 câu hỏi quy chế nội bộ và tối ưu hóa prompt generation.
