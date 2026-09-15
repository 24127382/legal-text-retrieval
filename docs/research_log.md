# Research state

Tài liệu này là index và current-state summary. Evidence, negative results và lịch sử quyết định đầy đủ được giữ theo research axis trong [`docs/research/`](research/).

Fixed DEV là split duy nhất dùng cho method selection và diagnostics. **Fixed local holdout** chỉ dùng để kiểm tra aggregate sau khi configuration đã freeze; đây không phải official competition test.

## Current validated LegalIR reference

```text
fixed character windows
chunk_size = 2000
overlap = 200

→ BAAI/bge-m3 dense retrieval
→ top 2000 chunks
→ sum top-2 dense chunk scores per document
→ top 100 documents
→ top-2 dense supporting chunks/document
→ BAAI/bge-reranker-v2-m3
→ sum of up to 2 CE chunk scores
→ top 5
```

Dense model có declared revision `5617a9f61b028005a4858fdac845db406aefb181`; reranker có declared revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Cả hai là offline snapshots; chỉ coi revision là được xác minh chính xác khi local model config có `_commit_hash` trùng declared revision.

| Split | Precision | Recall | MRR | Dense candidate Recall@100 |
|---|---:|---:|---:|---:|
| DEV | 0.18416988416988417 | 0.8647039897039897 | 0.7291748808854571 | 0.9819015444015444 |
| Fixed local holdout | 0.18338220918866083 | 0.8659986966438579 | 0.7299178380421532 | 0.9757249918540242 |

Dense→CE đã cải thiện cả precision và recall so với BM25→CE trên DEV và fixed local holdout, nên đây là current validated LegalIR reference.

## Current DEV-selected candidate

Dense→CE với `m=8` evidence pool: với mỗi fixed top-100 candidate document, CE
chấm tối đa 8 chunks từ original dense top-2.000 chunk pool, chọn top 2 evidence
chunks và sum hai CE scores trước final ranking. Configuration này cải thiện cả
precision, recall và MRR so với `m=2` trên fixed DEV và đang chờ
fixed-local-holdout validation. Current validated reference vẫn là `m=2`.

## Current observed bottleneck

Candidate retrieval không còn là dominant observed bottleneck. Trên DEV, dense candidate coverage tăng chậm khi mở rộng document depth:

| Candidate scope | Recall |
|---|---:|
| R@100 | 0.9819015444015444 |
| R@200 | 0.9877734877734878 |
| R@300 | 0.9905083655083654 |
| R@500 | 0.9929214929214928 |
| Full unique-document pool induced by top-2000 dense chunk hits | 0.9942084942084942 |

Supporting-evidence selection đã được xác nhận là một meaningful ranking
bottleneck trên DEV: `m=8` cải thiện precision, recall và MRR trong khi giữ nguyên
exact top-100 candidate documents. Residual ranking headroom vẫn còn sau `m=8`;
đây là DEV evidence, không phải absolute proof về mọi retrieval configuration.

## Frozen decisions

- **Dense retrieval:** BGE-M3 đã supersede BM25 như current validated single retriever sau khi Dense→CE cải thiện precision và recall trên cả DEV lẫn fixed local holdout.
- **Cross-encoder:** `BAAI/bge-reranker-v2-m3` tiếp tục là frozen validated reranker.
- **Final k:** giữ `k = 5`. Fixed `k=1..4` tạo precision/recall trade-off và không Pareto-improve so với `k=5`; điều này không chứng minh `k=5` universally optimal cho một combined metric chưa biết.
- **Candidate depth:** không ưu tiên tăng dense document candidate depth dựa trên diagnostic hiện tại.
- **Corpus representation:** source-preserving fixed windows `2000/200` vẫn là current validated representation.

## Rejected or deprioritized directions

- **Simple title enrichment:** reject formulation `document name + newline + raw chunk`; nó không cải thiện Recall@100, làm MRR giảm và làm deeper recall giảm nhẹ.
- **Article-aware representation:** chỉ giữ làm research candidate. Tín hiệu DEV là **small/mixed positive signal**: delta lần lượt là R@10 `-0.003056628056628208`, R@20 `+0.003619691119691182`, R@50 `-0.0001608751608751513`, R@100 `+0.0024131274131273805`, R@200 `-0.00024131274131278246`, và MRR `+0.011327197846623172`; số corpus chunks tăng từ `199816` lên `283260`. Không promote over fixed windows.
- **Larger dense document candidate depth:** deprioritized, không bị coi là một hướng “failed”; observed marginal coverage gain nhỏ hơn remaining final-ranking gap.

## Active validation

Supporting-evidence DEV experiment đã hoàn tất và chọn `m=8`. Standalone notebook
[`dense_cross_encoder_supporting_evidence_holdout.ipynb`](../notebooks/dense_cross_encoder_supporting_evidence_holdout.ipynb)
encode đúng một frozen comparison `m=2` vs `m=8` trên fixed local holdout. Notebook
chưa được chạy; chưa có holdout result mới và `m=8` chưa được promote.

## Detailed research history

- [`data_and_corpus.md`](research/data_and_corpus.md): raw-data audit, schema/corpus diagnostics, source provenance, fixed-window decisions và article-aware representation.
- [`legalir_retrieval.md`](research/legalir_retrieval.md): BM25, fixed split, document aggregation, dense retrieval/complementarity, DEV failure tables, title enrichment và candidate-depth diagnostic.
- [`legalir_reranking.md`](research/legalir_reranking.md): zero-shot CE, fixed-local-holdout validation, final-k comparison, Dense→CE DEV/holdout evidence và promotion decision.
