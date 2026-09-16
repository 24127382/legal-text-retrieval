# Research state

Tài liệu này chỉ giữ current state, decisions và active questions. Evidence và lịch sử đầy đủ được giữ theo research axis trong [`docs/research/`](research/).

Fixed DEV là split duy nhất dùng cho selection, tuning và sample-level diagnostics. Fixed local holdout chỉ dùng aggregate validation cho configuration đã freeze. Public leaderboard là external/public-test evidence, không phải DEV hay hyperparameter-search surface.

## Current public-inference / public-score reference

```text
fixed source-preserving windows: chunk_size=2000, overlap=200, step=1800
→ BAAI/bge-m3 dense top-2000 chunks
→ sum top-2 dense chunk scores/document
→ top-100 candidate documents
→ up to top-8 dense chunks/document from the original global top-2000 pool
→ BAAI/bge-reranker-v2-m3 scores every available support independently
→ select top-2 chunks by CE score
→ sum top-2 CE scores/document
→ deterministic ranking
→ top-5 unique document IDs
```

Best observed public score: `0.8935`. Tie-break: CE document score descending, original dense document rank ascending, rồi `document_id` ascending. Dense revision được khai báo là `5617a9f61b028005a4858fdac845db406aefb181`; reranker revision là `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Cả hai chạy từ local snapshot với `local_files_only=True`.

## Final-window focused research queue

Mọi neural checkpoint mới phải thỏa hard competition gate `parameter_count < 4_000_000_000` trước khi evaluation; notebook ghi actual loaded parameter count và dừng ngay nếu không đủ điều kiện. Đây là eligibility rule, không phải research axis.

Queue hiện chỉ giữ bốn high-upside questions và sáu standalone fixed-DEV notebooks:

1. Proper fixed-budget chunk fusion có phục hồi lexical signal mà naive uncapped document union đã làm mất không? So dense-only với equal-weight BM25+BGE RRF (`k=60`) và equal-weight per-query normalized-score fusion trong `bm25_bge_hybrid_fusion_dev.ipynb`.
2. Retrieval-only signal của fixed windows `2000/500` có sống qua frozen `candidate100 → m8 → CE top2/sum-top2` không? Kiểm tra trong `fixed_window_overlap500_cross_encoder_dev.ipynb`.
3. Retriever diversity có phục hồi BGE-M3 misses không? Đo GTE dense riêng, BGE+GTE chunk RRF downstream, và Jina ColBERT v2-64 late interaction trong ba notebook tương ứng; chưa tạo three-way hay second-stage combination.
4. Frozen BGE reranker có trở thành bottleneck không? So cùng exact candidate/support pairs với GTE multilingual reranker trong `gte_multilingual_reranker_dev.ipynb`.

Thứ tự execution: chạy ngay BM25+BGE fusion và overlap500 downstream; sau GTE dense upload chạy song song GTE retrieval và BGE+GTE hybrid; sau GTE reranker upload chạy reranker challenger; sau Jina upload chạy late-interaction challenger. Không notebook nào tự động đi vào holdout hoặc public inference.

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

## Detailed research history

- [`data_and_corpus.md`](research/data_and_corpus.md): raw-data audit, provenance, fixed-window variants và article-aware representation.
- [`legalir_retrieval.md`](research/legalir_retrieval.md): lexical/dense retrieval, document aggregation, candidate union, candidate depth và public evidence.
- [`legalir_reranking.md`](research/legalir_reranking.md): CE evidence routing/aggregation, fixed-local-holdout validations và public submission history.
