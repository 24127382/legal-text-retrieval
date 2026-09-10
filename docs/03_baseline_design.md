# 03 — Thiết kế baseline

## Nguyên tắc và trạng thái

```text
LegalIR: maximize candidate coverage first,
         then allocate at most five submission slots.
```

Retriever mới hữu ích chủ yếu khi tăng candidate coverage hoặc tạo lỗi bổ sung. Reranker mới hữu ích chủ yếu khi candidate coverage đã đủ cao nhưng final subset vẫn mất gold. B0 → B1 → B2 → B3 là research ladder, không phải tuyên bố các hệ thống đã được triển khai hay benchmark.

Trạng thái dùng trong tài liệu:

- `Code present`: có implementation/prototype; chưa suy ra validation.
- `Validated`: behavior đã được kiểm tra bằng test/artifact cụ thể.
- `Benchmarked`: có run đánh giá tái lập được.
- `Planned`: experiment đã được định nghĩa nhưng chưa chạy.
- `Research candidate`: đáng khảo sát nhưng chưa nằm trong baseline experiment hiện tại.
- `Speculative`: chi phí/rủi ro cao hoặc cơ sở hiện tại yếu.

## Năm tầng quyết định cần tách riêng

1. **Chunk retrieval**: lấy các đoạn có score/rank theo query.
2. **Candidate document construction**: map chunk về `document_id`, deduplicate document và giữ provenance của các chunk hỗ trợ.
3. **Document aggregation**: kết hợp nhiều chunk score/rank thành tín hiệu document.
4. **Reranking**: chấm lại chunk/document trong một candidate pool cố định bằng model mạnh hơn.
5. **Final subset selection**: chọn list 1–5 document ID để submit.

Thứ tự reranking và aggregation là một independent variable: có thể rerank chunk rồi aggregate, hoặc tạo representation document rồi rerank document. Mỗi run phải ghi rõ lựa chọn, không gọi chung mọi bước là “ranking”.

## B0 — lexical floor

```text
query → BM25 chunk/document retrieval
      → candidate document construction
      → document aggregation
      → final subset (1–5 document IDs)
```

Mục đích: tạo classical baseline dễ debug cho exact term, số hiệu văn bản, Điều/Khoản/Điểm và tên luật. Tokenization/normalization tiếng Việt, retrieval unit và aggregation là independent variables phải được log.

**Trạng thái:** `Planned`. Repository có thể chứa prototype liên quan, nhưng sự hiện diện của code không biến B0 thành `Validated` hay `Benchmarked`.

## B1 — hybrid retrieval

```text
                 ┌─ BM25 top-N ───┐
query ───────────┤                 ├→ union/fusion
                 └─ dense top-N ──┘
                                      ↓
                         candidate document construction
                                      ↓
                           aggregation → final subset
```

Dense control đầu tiên là BGE-M3 dense mode vì code prototype hiện có; multilingual-E5 chỉ là comparison candidate. Hai fusion hypothesis phải được so riêng:

- **Weighted/linear score fusion:** chuẩn hóa score từng retriever rồi tính `s = α s_bm25 + (1-α) s_dense`. Ghi rõ normalization, xử lý candidate chỉ có ở một nhánh và tune `α` chỉ trên validation.
- **Reciprocal Rank Fusion (RRF):** cộng `1/(k + rank)` theo nhánh. RRF tránh lệch raw-score scale nhưng bỏ magnitude; `k` là hyperparameter.

Không mặc định RRF thắng weighted fusion. Candidate depth, fusion, construction và aggregation phải được kiểm soát tách biệt.

## B2 — strong reference baseline

```text
                         ┌── BM25 top-N ─────┐
query ──────────────────┤                   ├→ candidate union/fusion
                         └── dense top-N ────┘
                                                   ↓
                                      cross-encoder reranking
                                                   ↓
                                      document construction
                                                   ↓
                                     document aggregation/ranking
                                                   ↓
                                    final subset: 1–5 document IDs
```

Khái niệm B2 được giữ cố định: **BM25 + dense retrieval → candidate union/fusion → cross-encoder → document aggregation/ranking → final selection**. Diagram là một instantiation ưu tiên; E06 có thể ablate vị trí aggregation/reranking nhưng phải giữ candidate pool so sánh được.

Các giá trị khởi đầu sau đều là **working hypotheses**, không phải fact hoặc kết quả:

- BM25 top 100;
- dense top 100;
- union rồi deduplicate theo `document_id` sau khi giữ chunk provenance;
- cross-encoder khoảng 50–200 candidates, tùy candidate recall, latency và memory;
- always-top-5 là final-selection control, nhưng output cuối phải được deduplicate và có độ dài 1–5.

Tune depth theo candidate-recall curve và compute. B2 ban đầu giữ retriever/reranker zero-shot hoặc frozen để tạo reference có attribution rõ. **Trạng thái B2: `Planned`; B2 là hệ tham chiếu nghiên cứu, không phải claim implementation.**

## B3 — domain-adapted strong baseline

B3 bắt đầu từ một B2 đã `Benchmarked`, rồi ablate từng addition riêng: title/parent context, aggregation, reranker tuning, dense tuning, conservative hard negatives, SPLADE, ColBERT, query diversification, pseudo-relevance feedback và distillation. Mỗi addition phải nêu control, independent variable, candidate coverage, final official scores, diagnostics và compute delta.

## Chunk → document

Repository-oriented design hiện index/retrieve chunk, trong khi submission LegalIR cần document ID:

```text
chunk hits + scores + ranks
        ↓ map/group by document_id
candidate documents + supporting chunks
        ↓ aggregate and/or rerank
document scores
        ↓ final subset
1–5 unique document IDs
```

`best chunk ≠ necessarily best document`: một chunk cao có thể là lexical accident; một document khác có thể có nhiều đoạn hỗ trợ nhất quán.

| Aggregation hypothesis | Cơ chế | Rủi ro cần đo |
|---|---|---|
| Max chunk | Score document bằng chunk cao nhất | Nhạy với một false-positive chunk. |
| Mean top-n | Trung bình n chunk tốt nhất | Có thể phạt document chỉ có một đoạn thật sự liên quan. |
| Weighted top-n | Trọng số giảm theo rank/score | Thêm hyperparameter và calibration. |
| Rank aggregation | Hợp rank của các chunk | Mất score magnitude. |
| Learned aggregator | Học từ score, rank, metadata, số chunk hỗ trợ | Dễ overfit; cần split/labels đáng tin. |

Báo diagnostics ở cả chunk và document level. Title/parent enrichment là representation variant; không tự động thay chunk boundaries và phải kiểm tra truncation, duplication, leakage.

## Official scorer và final subset

Official LegalIR scorer dùng set intersection. Vì vậy **order của các ID đã được submit không trực tiếp ảnh hưởng score**. Internal ranking vẫn thiết yếu vì nó quyết định document nào chiếm tối đa năm slot trước khi list được phát ra. Duplicate ID không có thêm credit, vẫn chiếm slot và có thể giảm precision.

| Final-selection rule | Cách làm | Trade-off |
|---|---|---|
| Always top-5 | Submit năm unique ID tốt nhất khi có đủ candidate | Bảo vệ recall; có thể thêm false positive. |
| Score threshold | Chỉ giữ candidate vượt ngưỡng, tối thiểu một ID | Phụ thuộc calibration/scale. |
| Margin rule | Dừng khi score gap đủ lớn | Nhạy distribution theo query. |
| Calibrated probability | Ước lượng xác suất relevant | Cần validation đại diện. |
| Adaptive k | Chọn 1–5 theo query | Có thể tăng precision nhưng mất recall. |

Không có artifact trong repository chứng minh recall là primary metric hay precision là tie-break; E14 phải báo cả hai official outputs thay vì tối ưu một quy tắc ưu tiên chưa xác minh.

## Reproducibility contract

Mỗi baseline run phải log: commit; data/split fingerprint; preprocessing; chunk/document index; model revision; tokenizer/max sequence length; candidate depths; score normalization; fusion; construction/deduplication; aggregation; reranker scope/depth; final-k rule; seed; hardware; runtime; index size; scorer artifact/hash.
