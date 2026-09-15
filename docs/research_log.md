# Research state

Tài liệu này chỉ giữ current state, decisions và active questions. Evidence và lịch sử đầy đủ được giữ theo research axis trong [`docs/research/`](research/).

Fixed DEV là split duy nhất dùng cho selection, tuning và sample-level diagnostics. Fixed local holdout chỉ dùng aggregate validation cho configuration đã freeze; đây không phải official competition test.

## Current validated LegalIR reference

```text
fixed character windows 2000/200
→ BAAI/bge-m3 dense top-2000 chunks
→ sum top-2 dense chunk scores/document
→ top-100 candidate documents
→ up to top-8 dense chunks/document from the original global top-2000 pool
→ BAAI/bge-reranker-v2-m3 scores every available support independently
→ select top-2 chunks by CE score
→ sum top-2 CE scores/document
→ deterministic ranking
→ top-5
```

Tie-break: CE document score descending, original dense document rank ascending, rồi `document_id` ascending. Dense revision được khai báo là `5617a9f61b028005a4858fdac845db406aefb181`; reranker revision là `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Cả hai chạy từ local snapshot với `local_files_only=True`.

Fixed-local-holdout metrics: precision `0.1884652981427175`, recall `0.8888074291300098`, MRR `0.7582601128237376`; dense candidate Recall@100 `0.9757249918540242`. Candidate documents giống hệt validated `m=2` control. DEV-selected `m=8` generalizes directionally trên fixed local holdout, nên `m=8` là current validated reference; `m=2` là superseded validated reference và vẫn được giữ trong empirical history.

## Current DEV-selected candidate

`candidate_depth=50` với toàn bộ stack `2000/200 + dense sum-top-2 + m8 + CE sum-top-2 + top5`. Trên DEV, depth 50 cải thiện nhẹ cả precision, recall và MRR so với depth 100, đồng thời dùng khoảng 43,86% ít CE pairs hơn. Configuration này đang chờ fixed-local-holdout validation; public inference vẫn giữ depth 100.

## Active DEV confirmation

- **CE title context:** tín hiệu DEV ban đầu dương nhưng notebook đã hoàn thành chưa có paired bootstrap. Cần confirmation DEV với candidate/support giống hệt control trước khi cân nhắc holdout.
- **Fixed windows `1000/100`:** dense retrieval signal dương/mixed; chỉ được promote sang downstream Dense→CE DEV evaluation, chưa validated và chưa được đưa vào public inference.

## Frozen decisions

- Giữ fixed windows `2000/200`, dense sum-top-2 document aggregation, frozen BGE reranker, CE sum-top-2 aggregation và final `k=5` trong current validated stack.
- Không tối ưu candidate Recall@100 riêng lẻ: coverage cao hơn có thể đi kèm final CE metrics thấp hơn.
- Chỉ một major research axis mỗi experiment; không combine depth 50, title context và `1000/100` trước khi từng signal được xác nhận độc lập.

## Closed or deprioritized

- Superseded `m=2` support pool.
- Article-aware representation trong current Dense→CE stack.
- Simple CE aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Simple dense aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Full-document support search ngoài global dense top-2000 evidence pool.
- Naive uncapped dense-top-100 ∪ BM25-top-100 candidate union; decision này không phủ định mọi vai trò của BM25.
- Fixed windows `3000/300`.

## Detailed research history

- [`data_and_corpus.md`](research/data_and_corpus.md): raw-data audit, provenance, fixed-window variants và article-aware representation.
- [`legalir_retrieval.md`](research/legalir_retrieval.md): lexical/dense retrieval, document aggregation, candidate union và candidate depth.
- [`legalir_reranking.md`](research/legalir_reranking.md): CE evidence routing/aggregation, fixed-local-holdout validations và title-context confirmation state.
