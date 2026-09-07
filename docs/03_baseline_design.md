# 03 — Thiết kế baseline

## Nguyên tắc

```text
LegalIR: maximize candidate coverage first,
         then allocate the final ≤5 slots with stronger relevance modeling.
```

Một retriever mới chỉ có giá trị chính nếu tăng candidate recall hoặc tạo lỗi bổ sung. Một reranker mới chỉ có giá trị chính nếu candidate recall đã cao nhưng final Recall@5 còn thấp. B0–B3 là ladder đo lường; không phải bốn cấu hình phải vận hành đồng thời.

## B0 — lexical floor

```text
query → BM25 → document aggregation → top-5 document IDs
```

Mục đích: tạo classical baseline có thể debug, đo sức mạnh exact term, số hiệu văn bản, Điều/Khoản và tên luật. Tokenization/normalization tiếng Việt là independent variable cần ghi lại.

**Trạng thái:** `main` chưa có BM25. `origin/feature/bm25` có lớp `BM25Okapi` tối thiểu; `version-1`/`ver2` có builder và search prototype. Vì chưa merge, B0 là `Planned`, không phải `Implemented`.

## B1 — hybrid retrieval

```text
                 ┌─ BM25 top-N ───┐
query ───────────┤                 ├→ union → fusion → document aggregation → top-5
                 └─ Dense top-N ──┘
```

Dense control đầu tiên là BGE-M3 hiện có; multilingual-E5 chỉ là comparison candidate. Thử hai hypothesis fusion riêng:

- **Alpha/linear score fusion:** chuẩn hóa score trong từng retriever rồi tính `s = α s_bm25 + (1-α) s_dense`. Phải ghi normalization (min-max, z-score, rank-based hoặc calibration set), xử lý candidate chỉ xuất hiện ở một nhánh, và tuning `α` chỉ trên validation.
- **Reciprocal Rank Fusion (RRF):** cộng `1/(k + rank)` theo nhánh. RRF tránh lệch raw-score scale nhưng bỏ qua magnitude. `k` là hyperparameter, không phải hằng số đúng cho mọi corpus.

Không mặc định RRF thắng alpha fusion. Candidate depth `N`, fusion và document aggregation phải được kiểm soát tách biệt.

## B2 — strong reference baseline

```text
                         ┌── BM25 top-N ─────┐
query ──────────────────┤                    ├→ union
                         └── BGE-M3 top-N ───┘
                                                  ↓
                                       alpha fusion / RRF
                                                  ↓
                                           candidate pool
                                                  ↓
                                          cross-encoder
                                                  ↓
                                      document-level ranking
                                                  ↓
                                     final selection: top-5
```

Điểm khởi đầu để kiểm chứng, không phải chân lý:

- BM25 top 100.
- Dense top 100.
- Union và deduplicate theo `document_id` sau khi giữ provenance của chunks.
- Cross-encoder khoảng 50–200 candidates tùy candidate recall, latency và memory.

Candidate depth phải tune theo đường cong candidate Recall@K và compute. B2 ban đầu giữ retriever/reranker zero-shot hoặc frozen, không fine-tune đồng thời mọi thành phần. Mục tiêu là reference system ổn định, reproducible và có attribution rõ.

## B3 — domain-adapted strong baseline

Bắt đầu từ B2 tốt nhất và ablate từng addition riêng:

1. title/legal-context enrichment;
2. chunk/document aggregation;
3. reranker fine-tuning;
4. dense retriever fine-tuning;
5. hard negatives;
6. SPLADE;
7. ColBERT;
8. query diversification;
9. PRF;
10. teacher–student distillation.

Không bật tất cả cùng lúc. Mỗi addition phải nêu control, independent variable, candidate recall/final metrics, error category và compute delta.

## Chunk-level retrieval và document-level ranking

Repository index chunks nhưng competition output là document IDs:

```text
query → chunk retrieval → chunk scores → document aggregation → document ranking
```

`best chunk ≠ necessarily best document`: một chunk nổi bật có thể là lexical accident; một document khác có nhiều chunks hỗ trợ nhất quán. Các aggregation hypothesis:

| Hypothesis | Cơ chế | Rủi ro cần đo |
|---|---|---|
| Max chunk | Score document bằng chunk cao nhất | Nhạy với một false-positive chunk. |
| Mean top-n | Trung bình n chunks tốt nhất | Penalize document chỉ có một đoạn thực sự liên quan. |
| Weighted top-n | Trọng số giảm theo rank/chunk score | Thêm hyperparameter và calibration. |
| Reciprocal/rank aggregation | Hợp nhất rank của chunks | Mất score magnitude. |
| Learned aggregator | Học từ score, rank, title, số support chunks | Dễ overfit; cần labels/split đáng tin. |

Phải deduplicate document trước final top-k và báo cả chunk-level lẫn document-level diagnostics. Title/parent context enrichment nên được tạo như representation variant, không sửa chunk boundaries trong task hiện tại. Cần tránh nhân bản title quá mức làm lexical score thiên lệch.

## Final top-k decision / calibration

Ranking và quyết định trả 1, 2, 3, 4 hay 5 documents là hai bài toán khác nhau:

| Rule | Cách làm | Trade-off |
|---|---|---|
| Always top-5 | Luôn dùng đủ 5 slot | Bảo vệ Recall nhưng có thể giảm Precision. |
| Score threshold | Chỉ trả candidate vượt ngưỡng | Phụ thuộc calibration và score scale. |
| Margin rule | Dừng khi chênh lệch score tăng mạnh | Nhạy với distribution theo query. |
| Calibrated probability | Ước lượng xác suất relevant | Cần validation đủ đại diện. |
| Adaptive k | Chọn k theo query | Có thể tăng Precision nhưng làm mất gold và giảm Recall. |

Always-top-5 là control bắt buộc. Không giả định adaptive-k tốt hơn khi Recall là objective chính.

## Reproducibility contract

Mỗi baseline run phải cố định và log: commit; data/split fingerprint; preprocessing; chunk index; model revision; max sequence length; retriever depths; score normalization; fusion hyperparameters; aggregation; reranker depth; final-k rule; random seed; hardware; runtime; index size.
