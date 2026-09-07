# 07 — Research roadmap

## Decision policy

Mỗi phase chỉ GO khi artifact đầu vào và metric của phase trước đủ tin cậy. Threshold số cụ thể phải được gắn nhãn **working hypothesis** và tune trên validation, không biến thành luật bất biến.

## Phase 0 — data và scorer verification

**Deliverables:** scorer test cases; split manifest/fingerprint; gold-document distribution; corpus/document/chunk statistics; metadata audit; rules về model/data/API; label-completeness audit.

- **GO:** local scorer khớp examples/official artifact, mapping ID rõ, ceiling được tính, split không leakage hiển nhiên.
- **NO-GO:** metric/output-limit chưa chắc chắn, duplicate/missing IDs, gold parse lỗi hoặc không có validation đáng tin. Không chạy model sweep để bù protocol mơ hồ.

## Phase 1 — B0/B1/B2 và diagnostics

Chạy E00–E04: BM25, BGE-M3, alpha fusion, RRF, cross-encoder. Log candidate recall curve, final Recall@5, overlap/unique gold và compute.

- **GO:** baseline reproducible và bottleneck được xác định.
- **NO-GO:** score thay đổi không giải thích được, encoding/index mismatch hoặc không deduplicate document.
- Nếu candidate Recall@100 gần bão hòa (working notion): không chỉ tăng retrieval breadth; ưu tiên reranking/final selection.
- Nếu candidate Recall@100 còn thấp: không chỉ thay generator/reranker; ưu tiên candidate retrieval.

## Phase 2 — representation và chunk→document

Chạy E05–E06: title, hierarchy/parent context và aggregation strategies; không đổi chunker trong documentation task.

- **GO:** gain lặp lại ở F07/F08 hoặc aggregate, không do duplicate/title leakage.
- **NO-GO:** chỉ tăng chunk score nhưng document recall không tăng, hoặc context enrichment gây truncation/regression.

## Phase 3 — reranker và hard-negative training

Chạy E07 theo curriculum random → semi-hard → hard → teacher-filtered.

- **GO:** final Recall@5 tăng trên cùng candidate pool, đặc biệt F05/F11, và false-negative audit chấp nhận được.
- **NO-GO:** candidate recall mới là bottleneck; labels không exhaustive; gain chỉ trên train/public leaderboard.

## Phase 4 — retriever adaptation

Chạy E08 và ablation contrastive fine-tuning, hard negatives, có điều kiện DAPT/TAPT hoặc synthetic queries.

- **GO:** candidate recall/unique-gold tăng ở depth có ích và generalize qua split.
- **NO-GO:** chỉ thay score calibration, collapse exact citations, hoặc training negatives đáng ngờ.

## Phase 5 — retrieval diversity

Chạy E09–E12: SPLADE, ColBERT, multi-query/legal rewrite và PRF. Original query luôn được giữ cho query-expansion branches.

- **GO:** unique gold và union recall đủ bù latency/index cost; error category mục tiêu cải thiện.
- **NO-GO:** overlap gần hoàn toàn, cùng gold misses, query drift hoặc compute tăng mà final metric không chuyển.

## Phase 6 — distillation và pseudo-labeling

Chạy E13 khi teacher đã validate. So hard-label, soft-score/margin distillation và filtered pseudo-label/self-training.

- **GO:** student tăng retrieval quality ở cùng hoặc thấp hơn inference cost; false-label audit đạt yêu cầu.
- **NO-GO:** student sao chép teacher bias, confirmation loop hoặc pseudo-label confidence không calibrated.

## Phase 7 — alternative formulations

Chạy E15 direct document-ID rồi mới cân nhắc E16 DSI/NCI generative retrieval.

- **GO:** branch recover unique gold, valid-ID rate cao và có giá trị ensemble trên fixed corpus.
- **NO-GO:** memorization theo query template, fail trên held-out/unseen documents, catastrophic identifiers hoặc training cost không tương xứng.

Đây là research alternatives, không thay B2 reference system.

## Phase 8 — LegalQA sau khi IR ổn định

Chạy QA0 oracle/closed-book, QA1 B2 RAG, QA2 extraction, QA3 verifier, QA4 formatting; chỉ sau đó mới xét FiD, IRCoT, Self-RAG/CRAG, PEFT, GraphRAG và joint IR–QA.

- **GO:** oracle gap chỉ rõ bottleneck và từng addition cải thiện đúng error type.
- **NO-GO:** retrieval chưa measurable, gold evidence mapping mơ hồ, hoặc metric gain đi kèm unsupported claims.

## Cross-phase gates

```text
candidate recall high + final recall low → ranking / aggregation / selection
candidate recall low  + final recall near candidate ceiling → retrieval
oracle QA high + end-to-end low → retrieval / evidence selection
oracle QA low → generator / reasoning / answer realization
```

Final top-k calibration E14 được chạy sau khi B2 ranking ổn định và scorer được xác minh. Always-top-5 luôn là control vì adaptive-k có thể hy sinh Recall.

## Dừng và quay lại

Dừng một family sau ít nhất một implementation đúng và một validation có attribution nếu: không tạo unique evidence, gain không lặp lại, cost vượt budget, hoặc error analysis cho thấy nó giải sai bottleneck. Null result vẫn được ghi vào [`05_experiment_map.md`](05_experiment_map.md) để tránh lặp lại thí nghiệm.
