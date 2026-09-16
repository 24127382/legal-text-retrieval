# Research state

Tài liệu này chỉ giữ current state, decisions và active questions. Evidence và lịch sử đầy đủ được giữ theo research axis trong [`docs/research/`](research/).

Fixed DEV là split duy nhất dùng cho selection, tuning và sample-level diagnostics. Fixed local holdout chỉ dùng aggregate validation cho configuration đã freeze; đây không phải official competition test.

## Current validated LegalIR reference

```text
fixed source-preserving windows: chunk_size=2000, overlap=200, step=1800
→ BAAI/bge-m3 dense top-2000 chunks
→ sum top-2 dense chunk scores/document
→ top-50 candidate documents
→ up to top-8 dense chunks/document from the original global top-2000 pool
→ BAAI/bge-reranker-v2-m3 scores every available support independently
→ select top-2 chunks by CE score
→ sum top-2 CE scores/document
→ deterministic ranking
→ top-5 unique document IDs
```

Tie-break: CE document score descending, original dense document rank ascending, rồi `document_id` ascending. Dense revision được khai báo là `5617a9f61b028005a4858fdac845db406aefb181`; reranker revision là `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Cả hai chạy từ local snapshot với `local_files_only=True`.

Fixed-local-holdout metrics: precision `0.1884652981427175`, recall `0.8894591072010427`, MRR `0.7584082641848077`; dense candidate Recall@50 `0.9679048550016293`. Depth 50 thỏa frozen accuracy decision rule và giảm `271790` CE pairs, tương đương khoảng `43.84%`, so với depth 100. Compute là secondary benefit, không phải lý do promotion.

Historical reference hierarchy: Dense→CE `m=2` / depth 100 là superseded validated reference; Dense→CE `m=8` / depth 100 là superseded validated reference; Dense→CE `m=8` / depth 50 là current validated reference. Tất cả historical results vẫn được giữ trong detailed research history.

## Frozen decisions

- Giữ fixed windows `2000/200`, dense sum-top-2 document aggregation, frozen BGE reranker, CE sum-top-2 aggregation và final `k=5` trong current validated stack.
- Không tối ưu candidate Recall@100 riêng lẻ: coverage cao hơn có thể đi kèm final CE metrics thấp hơn.
- Evidence hiện có phù hợp với diễn giải rằng bottleneck đã dần chuyển từ retrieval coverage sang ranking/evidence discrimination: `m=2 → m=8` tạo gain lớn và generalize trên holdout, còn depth 50 cải thiện nhẹ final ranking dù candidate recall thấp hơn. Article-aware chunks, naive BM25 union và windows `1000/100` có thể cải thiện coverage nhưng không tạo final top-5 gain tin cậy tương ứng; đây là evidence-supported interpretation, không phải causal proof.

## Closed or deprioritized

- Superseded `m=2` supporting-evidence policy.
- Candidate depth 100 trong vai trò current reference (superseded); historical validated results vẫn được giữ.
- Article-aware representation trong current Dense→CE stack.
- Simple CE aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Simple dense aggregation alternatives: max-top-1, mean-top-2, sum-top-3.
- Full-document support search ngoài global dense top-2000 evidence pool.
- Naive uncapped dense-top-100 ∪ BM25-top-100 candidate union; decision này không phủ định mọi vai trò của BM25.
- CE title-context prepend: small positive DEV point estimate, nhưng paired-bootstrap uncertainty chứa zero; không chọn cho holdout và deprioritize, không claim universally rejected.
- Fixed windows `3000/300`.
- Fixed windows `1000/100` trong current downstream stack: positive dense-retrieval signal nhưng weak/mixed downstream evidence; không chọn cho holdout, không claim representation này theoretically invalid.

## Detailed research history

- [`data_and_corpus.md`](research/data_and_corpus.md): raw-data audit, provenance, fixed-window variants và article-aware representation.
- [`legalir_retrieval.md`](research/legalir_retrieval.md): lexical/dense retrieval, document aggregation, candidate union và candidate depth.
- [`legalir_reranking.md`](research/legalir_reranking.md): CE evidence routing/aggregation, fixed-local-holdout validations và title-context confirmation state.
