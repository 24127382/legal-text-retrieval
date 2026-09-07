# 04 — Evaluation và diagnostics

## Tách official metric khỏi local diagnostics

**Official metric** là implementation do Ban Tổ chức cung cấp. **Local diagnostic** là phép đo hỗ trợ tìm bottleneck; nó không được gọi là official nếu chưa đối chiếu scorer. `src/metrics.py` hiện có Recall@K và MRR cơ bản, chưa tái tạo toàn bộ scoring protocol.

## Candidate retrieval metrics

Với gold set `G_q` và candidate pool đã deduplicate theo document `C_q^K`:

```text
candidate recall@K = |G_q ∩ C_q^K| / |G_q|
```

Báo cáo macro trung bình cho K = 10, 20, 50, 100 và 200 nếu compute có ý nghĩa. Đồng thời báo số query có recall bằng 0 và bằng 1; trung bình đơn lẻ có thể che retrieval miss nặng.

## Final ranking metrics

- Competition Recall@5 theo scorer đã xác minh.
- Precision@5 hoặc official precision definition; không tự suy diễn tie-break behavior.
- MRR và nDCG chỉ là offline diagnostics khi label format hỗ trợ.
- Với LegalQA: METEOR/ROUGE-L official cùng factuality/citation diagnostics nội bộ.

## Chẩn đoán bottleneck

```text
candidate recall@100 = 0.99
final recall@5       = 0.82
```

Candidate coverage gần bão hòa nhưng final selection mất nhiều gold: ưu tiên aggregation, reranking hoặc calibration.

```text
candidate recall@100 = 0.86
final recall@5       = 0.84
```

Final stage gần chạm ceiling của candidate pool: ưu tiên retrieval breadth, representation hoặc query diversification; thay reranker đơn thuần ít khả năng giải quyết.

## Mandatory pre-baseline: gold-document distribution

Với mỗi query:

```text
|G_q| = số gold relevant documents
```

Trước E00 phải báo: min, mean, median, p90, p95, max và tỷ lệ query có 1, 2, 3, 4, 5, >5 gold documents. Nếu standard recall tính trên mọi gold và output bị giới hạn 5:

```text
Recall_max(q) = min(5, |G_q|) / |G_q|
```

Đây là theoretical ceiling cần reconcile với official scorer. Báo macro ceiling và số query bị ceiling < 1. Kiểm tra label exhaustiveness qua duplicate/near-duplicate law, annotation pattern, unlabeled high-confidence candidates và manual audit có sampling protocol.

## Retriever complementarity

Mọi nhánh mới phải báo nhiều hơn aggregate Recall:

- candidate overlap, ví dụ Jaccard hoặc overlap@K;
- gold chỉ A recover;
- gold chỉ B recover;
- union recall;
- chi phí tăng thêm.

Áp dụng cho BM25–dense, dense–SPLADE, dense–ColBERT, original–rewritten query và original–PRF. Nếu candidate và recovered gold gần như trùng nhau, ensemble có thể chỉ tăng compute.

## Error analysis taxonomy

Mỗi query lỗi có thể mang nhiều nhãn:

| ID | Failure category | Câu hỏi chẩn đoán |
|---|---|---|
| F01 | Exact citation / identifier | Số hiệu, Điều/Khoản có bị tokenizer hoặc dense model làm mờ? |
| F02 | Legal terminology | Thuật ngữ hiếm có được lexical branch giữ? |
| F03 | Lay-language paraphrase | Semantic branch có bridge cách nói đời thường? |
| F04 | Synonym / vocabulary mismatch | Rewrite, SPLADE, dense hay PRF recover được gold? |
| F05 | Multiple highly similar laws | Reranker có phân biệt điều kiện pháp lý nhỏ? |
| F06 | Temporal/version ambiguity | Có chọn sai phiên bản/hiệu lực? Metadata có đủ không? |
| F07 | Title-dependent relevance | Chunk thiếu title/parent context? |
| F08 | Long-document/chunk aggregation | Gold chunk có nhưng document rank thấp? |
| F09 | Multi-document query | Giới hạn 5 và evidence coverage ảnh hưởng thế nào? |
| F10 | Retrieval miss | Gold không vào candidate pool ở depth đo? |
| F11 | Reranker misordering | Gold vào pool nhưng rơi khỏi final top-5? |
| F12 | False-negative label suspicion | Candidate có vẻ relevant nhưng không được gắn label? |

Mỗi experiment report phải nêu category cải thiện, category hồi quy và ví dụ đã ẩn thông tin nhạy cảm nếu cần; aggregate gain không đủ.

## Conservative hard-negative protocol

Nguồn: BM25 near-miss, dense near-miss, cross-encoder disagreement, cùng topic nhưng sai điều kiện, cùng law family nhưng sai article/document.

```text
random negatives → semi-hard negatives → hard negatives
                 → teacher-filtered hard negatives
```

Không coi mọi unlabeled document là guaranteed negative khi label completeness chưa xác minh. Lưu provenance, rank và teacher score; manual-audit một sample; giữ ambiguous examples ngoài loss hoặc dùng soft label. **Teacher-generated hard negatives** là cách chọn negative; **distillation** là học score distribution/margin của teacher — hai khái niệm không đồng nhất.

## Final-selection diagnostics

So sánh always-top-5 với threshold, margin, calibrated probability và adaptive-k. Báo theo query: k được chọn, gold retained, extra false positives, calibration error (nếu có) và Recall loss. Không chọn adaptive-k chỉ vì Precision tăng nếu Recall chính giảm.

## Kiểm soát thí nghiệm

- Một major axis mỗi experiment; các component còn lại fixed.
- Validation độc lập với public leaderboard; tránh repeated leaderboard tuning.
- Cùng candidate pool khi so reranker; cùng reranker khi so retriever.
- Báo confidence interval hoặc paired bootstrap khi sample cho phép.
- Ghi failed run và null result; không chỉ ghi best score.
