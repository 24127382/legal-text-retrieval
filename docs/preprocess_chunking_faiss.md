# BÁO CÁO KIẾN TRÚC & TÀI LIỆU KỸ THUẬT PIPELINE
## Vietnamese Legal RAG: Preprocessing, Structure-Aware Chunking & FAISS Indexing

---

## 1. System Overview (Tổng quan Hệ thống)

Hệ thống được thiết kế theo dạng **Pipeline nối tiếp (Multi-stage Pipeline)** với mục tiêu biến đổi dữ liệu văn bản pháp lý Việt Nam dạng thô (Raw JSON/PDF/OCR) thành không gian vector (Vector Space) được đánh chỉ mục tối ưu cho các tác vụ RAG (Retrieval-Augment Generation).

### 1.1. Sơ đồ Luồng dữ liệu (Dataflow Pipeline)

```
[Raw Legal JSON / OCR Text]
           │
           ▼ (Stage 1: Parsing & Normalization)
[Cleaned CSV] ──► [Metadata JSONL] (Intermediate Representation with Fingerprint & Offsets)
           │
           ▼ (Stage 2: Structure-Aware Chunking)
[Chunks CSV]  ──► [Chunks JSONL & Stats JSON] (Zero Text Loss & Boundary Preserved)
           │
           ▼ (Stage 3: Embedding & Indexing)
[BAAI/bge-m3 Transformer] ──► [FAISS Index (IndexFlatIP)] + [chunk_ids.json Mapping]
```

---

## 2. Preprocessing & Structural Parsing

Giai đoạn này không đơn thuần là "làm sạch văn bản" (clean text), mà đóng vai trò tạo ra một **Intermediate Representation (IR)** trích xuất đầy đủ cấu trúc pháp lý và bảo toàn vị trí (offsets) nguyên bản.

### 2.1. Text Normalization (Conservative Cleaning)
Mục tiêu chính là loại bỏ các nhiễu sinh ra từ quá trình trích xuất PDF/OCR mà **không làm thay đổi thông tin pháp lý**.
* **Xử lý cụ thể:** Loại bỏ ký tự điều khiển (control characters), khoảng trắng thừa, dải newline liên tiếp, thanh phân cách (separator lines) dạng `---` hoặc `===`.
* **Nguyên tắc Conservative Preprocessing:** Chỉ xử lý artifact có độ tin cậy cao. Đối với văn bản pháp lý, các chuỗi như `Nghị định 100/2019/NĐ-CP`, `Điều 1`, `Khoản 2`, `Điểm a)` là thông tin cấu trúc cốt lõi, tuyệt đối không được xóa hoặc làm biến dạng.

### 2.2. Structural Parsing & Fingerprint Trích xuất
Parser nhận diện cây cấu trúc phân cấp pháp lý:
$$	ext{Document} 
ightarrow 	ext{Part} 
ightarrow 	ext{Chapter} 
ightarrow 	ext{Section} 
ightarrow 	ext{Article} 
ightarrow 	ext{Clause} 
ightarrow 	ext{Point}$$

Mỗi đơn vị cấu trúc được gắn metadata về tọa độ ký tự (`char_start`, `char_end`) và loại cấp độ (`level`). Từ đó, parser tạo ra **Structural Fingerprint** cho mỗi văn bản (ví dụ: `["part", "chapter", "article", "clause", "point"]` hoặc `["article", "clause"]`). Fingerprint này quyết định chiến lược phân chia chunk ở giai đoạn sau.

### 2.3. Metadata + Offset Preservation
Parser lưu giữ các trường thông tin then chốt: `document_id`, `document_title`, cấu trúc chương/điều/khoản, cùng chỉ số offset chính xác. Điều này đảm bảo chunker hiểu rõ ranh giới ngữ nghĩa thay vì cắt mù.

---

## 3. Tokenization Decision (Quyết định Kiến trúc: Tại sao KHÔNG WordBreak?)

Một quyết định kiến trúc quan trọng trong pipeline là **loại bỏ bước tách từ explicit (Word Segmentation như `underthesea` / `VnCoreNLP`)**.

```
[Tiếp cận truyền thống]
Raw Text ──► WordBreak (thông_tin, Nghị_định) ──► Cleaning ──► Chunking ──► Embedding

[Tiếp cận hiện tại]
Raw Text ──► Conservative Cleaning ──► Structure-Aware Chunking ──► BGE-M3 Subword Tokenizer
```

### 3.1. Phân tích Trade-off & Phát hiện EDA
* **Đặc thù lỗi Legal Corpus:** Lỗi trong dữ liệu pháp lý chủ yếu nằm ở ký tự PDF/OCR, cấu trúc header/numbering, ký hiệu số hiệu (`Điều 1-a`, `100/2019/NĐ-CP`), thuật ngữ chuyên ngành. 
* **Nguy cơ biến đổi Representation:** Tách từ thủ công dễ làm biến dạng các chuỗi ký hiệu kỹ thuật, URL/Path, hoặc ký hiệu phân cấp có dấu gạch nối (`-`).
* **Khả năng của Subword Tokenizer:** Mô hình **`BAAI/bge-m3`** sử dụng Subword Tokenization (BPE/Byte-fallback) hiện đại. Mô hình tự học ngữ cảnh tiếng Việt và từ ghép hiệu quả mà không phụ thuộc vào tiền xử lý dấu gạch dưới (`_`).

### 3.2. Đơn giản hóa Kiến trúc
Bỏ bước WordBreak giúp giảm độ phức tạp dependency, tăng tốc độ tiền xử lý pipeline lên nhiều lần và tránh nguy cơ lây lan lỗi (error propagation) từ mô hình Word Segmentation.

---

## 4. Structure-Aware Chunking (Kỹ thuật Cắt Chunks theo Cấu trúc)

### 4.1. Thuật toán Chunking Phân cấp
Chunker vận hành theo nguyên tắc **Structure First, Size Second**.

```
               Structural Unit (Part / Chapter / Section / Article)
                                      │
                                      ▼
                                 ≤ 6,000 chars?
                                 /                                         YES           NO
                                │             │
                                ▼             ▼
                            Keep Unit     Go Deeper
                                          (Article ➔ Clause ➔ Paragraph)
                                                      │
                                                      ▼
                                                 > 6,000 chars?
                                                      │
                                                      ▼
                                               Hard Character Split
```

### 4.2. Giới hạn Ngưỡng (Soft Limit & Hard Limit)
* **Soft Limit (5,000 ký tự):** Ngưỡng mục tiêu đóng gói (Target Packing Boundary). Nếu `current_size + next_unit_size <= 5,000`, tiếp tục gom cụm.
* **Hard Limit (6,000 ký tự):** Upper Bound tuyệt đối. Nếu một khối ngữ nghĩa chuẩn bị vượt quá 6,000 ký tự, chunker dừng gom cụm và đóng chunk.
* **Hard Structural Boundary:** Các cấp độ cao như `Part`, `Chapter`, `Section` được coi là ranh giới cứng (Hard Boundary). Pipeline không gom 2 Chương khác nhau vào cùng 1 chunk chỉ để lấp đầy `target_size`, đảm bảo tính toàn vẹn ngữ cảnh.

### 4.3. Zero Text Loss Invariant (Bảo toàn 100% Văn bản)
Pipeline thiết lập ràng buộc invariants khắt khe:
$$	ext{Chunk}_0.	ext{char\_start} = 0$$
$$	ext{Chunk}_i.	ext{char\_end} = 	ext{Chunk}_{i+1}.	ext{char\_start}$$
$$	ext{Chunk}_n.	ext{char\_end} = 	ext{len}(	ext{Source Document})$$
$$	ext{Chunk}_i.	ext{text} \equiv 	ext{Source}[	ext{char\_start}:	ext{char\_end}]$$

---

## 5. Quality Control & Validation Results

Hệ thống tích hợp bộ tự động kiểm thử (QC Engine) kiểm tra 100% output chunks trước khi chuyển sang giai đoạn Embedding.

### 5.1. Kết quả Validation Thực tế
* **Tổng số văn bản xử lý:** 8,512 documents
* **Tổng số chunks sinh ra:** 94,717 chunks
* **Số lỗi Schema:** 0
* **Số lỗi Mismatch Source:** 0
* **Số lỗi Overlap / Gap (Text Loss):** 0
* **Số chunks vi phạm Hard Limit (> 6,000 chars):** 0

### 5.2. Phân bố Độ dài Chunk (Length Buckets)

| Khoảng độ dài (Ký tự) | Số lượng Chunks | Tỷ lệ (%) | Ý nghĩa Kiến trúc |
| :--- | :--- | :--- | :--- |
| **< 1,000** | 12,124 | 12.8% | Các Điều/Khoản ngắn hoặc phần kết chương |
| **1,000 – 3,000** | 20,648 | 21.8% | Đơn vị Điều/Khoản độc lập vừa phải |
| **3,000 – 5,000** | 24,816 | 26.2% | Cụm gom ngữ nghĩa đạt ngưỡng tối ưu |
| **5,000 – 5,500** | 27,184 | 28.7% | Ngưỡng gom sát Soft Limit |
| **5,500 – 6,000** | 9,945 | 10.4% | Cụm lớn tiệm cận Hard Limit |
| **> 6,000** | 0 | 0.0% | **Đảm bảo 100% không bị tràn context** |

---

## 6. Embedding & FAISS Vector Indexing

* **Embedding Model:** `BAAI/bge-m3` (Hỗ trợ context 8,192 tokens, 1024 dimensions).
* **Chuẩn hóa Vector:** Vector được chuẩn hóa L2 (`normalize_embeddings=True`).
* **FAISS Index Type:** `faiss.IndexFlatIP` (Inner Product). Trên không gian vector đã chuẩn hóa L2, phép tính Inner Product chính xác bằng Cosine Similarity nhưng cho tốc độ truy vấn tối ưu.
* **ID Alignment:** Ma trận Vector được lưu cùng `chunk_ids.json` đảm bảo truy xuất lại 100% metadata từ `chunks.jsonl`.

---

## 7. Vận hành & Vẫn chạy Repo (Setup & Execution Guide)

### 7.1. Cài đặt Môi trường
```bash
pip install pandas pyarrow PyYAML sentence-transformers torch faiss-cpu
```

### 7.2. Cấu trúc Thư mục Dự án
```
legal-text-retrieval/
├── data/
│   └── raw/               # Giải nén dữ liệu thô (.json/PDF/OCR) đặt tại đây
├── src/
│   ├── parser.py          # Stage 1: Text normalization & Legal parsing
│   ├── chunker.py         # Stage 2: Structure-aware chunking algorithm
│   └── pipeline.py        # Pipeline runner & FAISS indexing stage
├── output/
│   ├── metadata.jsonl     # Kết quả Stage 1
│   ├── chunks.jsonl       # Kết quả Stage 2 (dạng JSONL)
│   ├── chunks.csv         # Kết quả Stage 2 (dạng CSV)
│   ├── chunking_stats.json# Báo cáo thống kê QC
│   ├── faiss.index        # FAISS Index File (Sinh ra khi run_embedding=True)
│   └── chunk_ids.json     # ID Mapping File (Sinh ra khi run_embedding=True)
└── requirements.txt
```

### 7.3. Thực thi Pipeline
Chạy toàn bộ quy trình qua lệnh Python:
```python
from src.pipeline import run_full_pipeline

stats = run_full_pipeline(
    input_dir="data/",
    output_dir="output/",
    run_embedding=True,
    model_name="BAAI/bge-m3"
)
print("Pipeline hoàn tất thành công:", stats)
```
> ⚠️ **LƯU Ý QUAN TRỌNG VỀ HIỆU NĂNG (HARDWARE REQUIREMENT):**
> 
> * **Stage 1 & Stage 2 (Parsing & Chunking):** Có thể chạy mượt mà trên môi trường CPU Local (thời gian xử lý 8,500 documents ~ 1-2 phút).
> * **Stage 3 (Embedding & FAISS Indexing):** Ma trận dữ liệu 94,717 chunks $\times$ 1,024 dims ($\approx 388 \text{ MB}$) yêu cầu phần toán Self-Attention phức tạp. **BẮT BUỘC phải chạy trên phần cứng hỗ trợ GPU (Google Colab T4/A100 hoặc GPU server)**. Thời gian chạy trên GPU chỉ mất ~15-20 phút, nhưng nếu chạy trên CPU sẽ mất hàng trăm giờ.
> * Mặc định trong code, `run_embedding` được đặt là `False`.