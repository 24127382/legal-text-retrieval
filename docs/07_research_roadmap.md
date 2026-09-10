# 07 — Research roadmap

## Decision policy

Mỗi phase chỉ GO khi artifact/metric cần thiết đủ tin cậy. Threshold số phải là **working hypothesis** preregistered và tune trên validation. `Code present` không mở gate validation; `Benchmarked` cần reproducible run artifact.

## Dependency overview

```text
scorer/data verification
        ├── QA0 controls/oracle, if reliable gold evidence exists
        │
        └── LegalIR B0/B1/B2
                  ↓
                 QA1
                  ↓
              QA2 → QA3 → QA4
```

QA0 closed-book có thể chạy khi QA scorer/data/generator control sẵn sàng. QA0 oracle có thể chạy sớm chỉ khi reliable gold-evidence mapping tồn tại; không cần chờ toàn bộ LegalIR roadmap.

## Phase 0 — scorer và data verification

**Resolved:** official LegalIR/LegalQA scorer contracts đã có trong `scoring/` và được document bằng code inspection.

**Still planned:** executable scorer test cases/environment fingerprint; split manifest; leakage audit; gold-document distribution/maximum-5 ceiling; label-completeness signals; metadata audit; external model/data/API rules; LegalQA gold-evidence mapping.

- **GO theo từng nhánh:** scorer reproduction khớp artifact; schema/key mapping rõ; required data dependency của experiment đã được audit.
- **NO-GO:** prediction/reference keys sai, gold parse lỗi, split leakage rõ, hoặc experiment cần gold mapping chưa tồn tại.

D00 không được đánh dấu hoàn tất chỉ vì scorer source đã có.

## Phase 1 — LegalIR B0/B1/B2

Chạy E00–E04: BM25, BGE-M3 control, weighted fusion, RRF, cross-encoder. Log candidate Recall@K curve, zero/full-recall rates, official `recall`/`precision`, overlap/unique gold, chunk→document behavior và compute.

- **GO:** run tái lập được và bottleneck được xác định.
- **NO-GO:** score không ổn định/không giải thích được, encoding/index mismatch hoặc document deduplication sai.
- Candidate coverage cao nhưng final official recall thấp: ưu tiên aggregation/reranking/subset selection.
- Candidate coverage thấp và final gần candidate ceiling: ưu tiên retrieval/representation.

“Cao/thấp” là threshold working hypothesis, không phải fact hiện tại.

## Phase 2 — representation và chunk→document

Chạy E05–E06: title/parent context và aggregation. Tách candidate construction, aggregation và reranking.

- **GO:** gain lặp lại trên held-out/aggregate và target error category, không do duplicate/title leakage.
- **NO-GO:** chỉ tăng chunk score nhưng không tăng document outcome, hoặc enrichment gây truncation/regression.

## Phase 3 — reranker/hard negatives

Chạy E07 theo conservative negative curriculum sau label audit.

- **GO:** official scores/final subset cải thiện trên cùng candidate pool, đặc biệt F05/F11; false-negative audit chấp nhận được.
- **NO-GO:** candidate retrieval vẫn là bottleneck; labels không đủ; gain chỉ ở train/public tuning.

## Phase 4 — retriever adaptation

Chạy E08; DAPT/TAPT hoặc synthetic queries chỉ là conditional research candidates.

- **GO:** candidate coverage/unique gold tăng tại depth hữu ích và generalize qua split.
- **NO-GO:** chỉ đổi calibration, làm hỏng exact citation hoặc dùng negative đáng ngờ.

## Phase 5 — retrieval diversity

Chạy E09–E12: SPLADE, ColBERT, query variants và PRF. Original query luôn được giữ ở expansion branches.

- **GO:** unique gold/union recall bù latency/index cost và cải thiện đúng error category.
- **NO-GO:** overlap gần hoàn toàn, cùng gold misses, query drift hoặc compute tăng không tạo final gain.

## Phase 6 — distillation/pseudo-labeling

Chạy E13 khi teacher đã `Validated` và `Benchmarked`. Ablate hard labels, soft scores/margins và filtered pseudo-labeling.

- **GO:** student tăng retrieval quality ở cùng/thấp hơn inference cost; false-label audit đạt yêu cầu.
- **NO-GO:** sao chép teacher bias, confirmation loop hoặc confidence không calibrated.

## Phase 7 — alternative LegalIR formulations

Chạy E15 direct document-ID trước khi cân nhắc E16 generative retrieval.

- **GO:** recover unique gold, valid-ID rate cao và có ensemble value.
- **NO-GO:** memorization, unseen-document failure, catastrophic identifier hoặc cost không tương xứng.

Các hướng này không thay B2 reference system. E14 final subset calibration chạy sau khi B2 ranking ổn định; always-top-5 là control và cả official recall/precision đều phải báo.

## LegalQA track

### QA0 — early controls

Chạy closed-book khi scorer/data/generator fixed. Chạy gold-evidence oracle khi mapping đã verified.

- **GO:** control reproducible và error attribution có ý nghĩa.
- **NO-GO:** mapping gold mơ hồ, prompt/parser không fixed hoặc scorer reproduction sai.

### QA1 — after LegalIR B2 benchmark

So retrieve–rerank–generate với no-rerank RAG trên cùng generator/context policy.

- **GO:** selected evidence/official metric thay đổi đúng hypothesis.
- **NO-GO:** B2 chưa measurable, comparison thay nhiều axis hoặc evidence trace thiếu.

### QA2 → QA3 → QA4

QA2 ablate span selection; QA3 ablate verifier; QA4 chỉ thay answer realization sau factual support. Mỗi bước giữ fixed component theo [experiment map](05_experiment_map.md).

- **GO:** addition cải thiện target diagnostic hoặc official metric mà không che regression quan trọng.
- **NO-GO:** metric gain đi kèm unsupported claims/dropped legal conditions, hoặc verifier/selector chưa được audit.

FiD, iterative RAG/IRCoT, Self-RAG/CRAG, PEFT, GraphRAG và joint IR–QA là later-stage research, không phải prerequisite của QA baseline.

## Cross-track gates

```text
candidate recall high + final recall low → aggregation / reranking / subset selection
candidate recall low  + final near ceiling → retrieval
oracle QA high + end-to-end low           → retrieval / evidence selection
oracle QA low                              → generator / reasoning / realization or mapping audit
```

## Dừng và quay lại

Dừng một family sau ít nhất một implementation đúng và một validation có attribution nếu nó không tạo unique evidence, gain không lặp lại, cost vượt budget hoặc error analysis cho thấy giải sai bottleneck. Ghi null/failed run vào [05 — Experiment map](05_experiment_map.md); không biến null result thành claim method vô dụng trên mọi setting.
