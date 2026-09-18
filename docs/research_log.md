# Research state

Tài liệu này chỉ giữ current state, decisions và active questions. Evidence và lịch sử đầy đủ được giữ theo research axis trong [`docs/research/`](research/).

Fixed DEV là split duy nhất dùng cho selection, tuning và sample-level diagnostics. Fixed local holdout chỉ dùng aggregate validation cho configuration đã freeze. Public leaderboard là external/public-test evidence, không phải DEV hay hyperparameter-search surface.

## Selected competition-time public deployment

```text
fixed source-preserving windows: chunk_size=2000, overlap=200, step=1800
→ BAAI/bge-m3 normalized CLS top-2000 chunks
+ BM25S 0.3.11 Lucene top-2000 chunks
→ per-query min-max score normalization
→ 0.50 * dense + 0.50 * BM25
→ fused top-2000 chunks
→ sum top-2 hybrid chunk scores/document
→ candidate depth 100
→ up to top-8 hybrid chunks/document from the fused top-2000 pool
→ BAAI/bge-reranker-v2-m3 scores every available support independently
→ select top-2 chunks by CE score
→ sum top-2 CE scores/document
→ final score = 1/(60 + CE rank) + 0.25/(60 + original BGE dense rank)
→ top-5 unique document IDs
```

DEV-selected candidate metrics: precision `0.19420849420849426`, recall `0.9105534105534104`, MRR `0.7710374420013412`. So với dense→CE baseline (`0.19150579150579153`, `0.8973616473616474`, `0.7622471799366903`), delta lần lượt là `+0.00270270270270273`, `+0.0131917631917630`, `+0.0087902620646509`. Paired-bootstrap 95% CI là precision `[0.0009652509652509653, 0.004633204633204633]`, recall `[0.005308880308880309, 0.02171814671814672]`; fraction delta > 0 là `0.9979` và `0.9996`.

Đây là **competition-time deployment decision** ngày 2026-09-18. Fixed local holdout được chủ động bỏ qua vì thời gian thi còn lại quá ngắn; đây không phải khuyến nghị thay đổi research protocol thông thường. Không tune thêm weight/lambda và không mở experiment mới. Notebook public chỉ dùng 1.000 câu hỏi unlabeled; không đọc answer labels hay chạy evaluation.

## Previous public-score reference remains unchanged

Best observed public score vẫn là `0.8935` từ S3 cho đến khi candidate mới có public score thực tế; không suy diễn hay ghi đè score này. S3 dùng fixed `2000/200` → BGE-M3 dense top-2000 → dense sum-top-2 → candidate 100 → `m=8` → CE select top-2/sum-top-2 → deterministic top-5.

Dense revision là `5617a9f61b028005a4858fdac845db406aefb181`; reranker revision là `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Public notebook load local snapshot với `local_files_only=True` và hard-fail nếu actual loaded parameter count của bất kỳ neural model nào không nhỏ hơn `4_000_000_000`.

Research cho submission này đã freeze; không còn next batch trước submission.

## Compute-efficient validated alternative

Dense→CE `m=8` / candidate depth 50 giữ nguyên toàn bộ stack trên và chỉ giảm candidate depth từ 100 xuống 50. Fixed-local-holdout metrics: precision `0.1884652981427175`, recall `0.8894591072010427`, MRR `0.7584082641848077`; CE pairs `348153`, giảm `0.43841127329448026` (khoảng `43.84%`) so với depth 100. Public score là `0.8915`.

Depth 50 đã thỏa pre-frozen local-holdout promotion rule và vẫn là **fixed-local-holdout-validated compute-efficient variant**. Kết quả này không bị xóa hay gọi là failed experiment. Tuy nhiên depth 100 có public score cao hơn (`0.8935` so với `0.8915`), nên depth 100 được đặt lại làm **current public-score / public-inference reference**.

## Public evidence history

Bốn kết quả dưới đây là **external/public-test evidence**, không phải DEV selection evidence:

| Submission | Public score | Method |
|---|---:|---|
| S1 | `0.8530` | BM25 → CE, `m=2`, candidate depth 100 |
| S2 | `0.8685` | Dense → CE, `m=2`, candidate depth 100 |
| S3 | `0.8935` | Dense → CE, `m=8`, candidate depth 100 |
| S4 | `0.8915` | Dense → CE, `m=8`, candidate depth 50 |

Sequence này cho thấy positive public movement rõ từ BM25→Dense và từ `m=2`→`m=8`, rồi small negative public movement khi depth 100→50. Đây là controlled historical evidence theo các thay đổi được Git xác nhận, nhưng không phải causal isolation vượt quá các method changes đó.

The public leaderboard has now been observed for four submissions. It is treated as external evidence, not as a hyperparameter search surface. Không test depth 60/70/80/90 dựa trên public leaderboard feedback; không dùng public score để tune fusion weight, chunk parameter hay submit lặp lại mọi DEV variant. Candidate-depth tuning axis được đóng ở 50/100.

## Frozen decisions

- Accuracy-oriented DEV experiments mới dùng depth-100 + `m=8` control với raw support chunks, dense sum-top-2, CE select top-2/sum-top-2 và final `k=5`.
- Giữ fixed windows `2000/200`, dense sum-top-2 document aggregation, frozen BGE reranker, CE sum-top-2 aggregation và final `k=5` trong current public stack.
- Không tối ưu candidate coverage riêng lẻ: coverage cao hơn không bảo đảm final CE metrics cao hơn.
- Không tự động promote kết quả DEV vào holdout hoặc public inference.

## Closed or deprioritized

- Article-aware representation trong current Dense→CE stack.
- Simple dense aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Simple CE aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Full-document support search ngoài global dense top-2000 evidence pool.
- Naive uncapped dense-top-100 ∪ BM25-top-100 candidate union.
- CE title-context prepend.
- Fixed windows `1000/100` trong downstream candidate stack.
- Fixed windows `3000/300`.
- Candidate-depth tuning ngoài hai depth 50/100 đã kiểm tra.
- Fixed windows `2000/500` dưới current downstream stack.
- GTE dense retrieval challenger và Jina ColBERT challenger.

## Detailed research history

- [`data_and_corpus.md`](research/data_and_corpus.md): raw-data audit, provenance, fixed-window variants và article-aware representation.
- [`legalir_retrieval.md`](research/legalir_retrieval.md): lexical/dense retrieval, document aggregation, candidate union, candidate depth và public evidence.
- [`legalir_reranking.md`](research/legalir_reranking.md): CE evidence routing/aggregation, fixed-local-holdout validations và public submission history.
