# 07 — Research roadmap

## Decision policy

Mỗi phase chỉ GO khi artifact/metric cần thiết đủ tin cậy. Threshold số phải là **working hypothesis** preregistered và tune trên validation. `Code present` không mở gate validation; `Benchmarked` cần reproducible run artifact.

## Dependency overview

```text
P00 scorer/protocol verification
          ↓
D00 raw data audit
          ↓
D01/D02 normalization + structure validation
          ↓
C0 canonical corpus baseline + D06 integrity gate
          ↓
          ├────────────── LegalIR B0 → B1 → B2
          │                            ↓
          │                           QA1
          │                            ↓
          │                       QA2 → QA3 → QA4
          │
          └── QA0 controls when their own dependencies are available
```

QA0 closed-book không cần LegalIR corpus và có thể chạy khi QA scorer/data/generator control sẵn sàng. QA0 gold-evidence oracle có thể chạy sớm chỉ khi reliable gold-evidence mapping tồn tại và được verify. End-to-end retrieved-evidence QA cần canonical evidence records và một retrieval/evidence pipeline measurable.

## Phase 0 — protocol/scorer verification

**Resolved:** official LegalIR/LegalQA scorer contracts đã có trong `scoring/` và được document bằng code inspection.

**Still planned trong P00:** executable scorer test cases, valid/invalid submission fixtures, scorer hash, environment/package fingerprint và deterministic outputs.

- **GO:** local reproduction khớp organizer artifact và submission behavior được test.
- **NO-GO:** prediction/reference keys hoặc outputs lệch scorer; runtime không tái lập.

P00 không hoàn thành D00: scoring truth và raw-data truth là hai authority layers riêng.

## Phase 1 — raw data + corpus contract

Chạy D00 raw schema/split audit và thiết lập immutable input manifests/fingerprints. Audit missing/duplicate IDs, empty/null values, gold-document distribution/maximum-5 ceiling, leakage signals, label completeness, metadata availability và LegalQA gold-evidence mapping.

- **GO:** mỗi raw record/split được manifest; exceptions và unknowns explicit; không silent loss/ID remap.
- **NO-GO:** schema/source ambiguity chưa resolve, leakage nghiêm trọng chưa có policy hoặc gold ID không map được khi task yêu cầu.

Không commit/copy raw competition data; chỉ lưu config, manifests/fingerprints và aggregate validation artifacts phù hợp policy.

## Phase 2 — canonical corpus baseline / preprocessing validation

Chạy D01 minimal normalization, D02 legal-structure parsing QC và D06 provenance/corpus-index integrity để freeze C0. C0 dùng policy đơn giản, deterministic, auditable; không cần chứng minh là chunk strategy tốt nhất.

- **GO:** source-preserving representation, explicit `source_text`/`retrieval_text`, complete chunk→document→source provenance, deterministic regeneration và manifest/index consistency.
- **NO-GO:** silent parse skip/document loss; orphan/duplicate không giải thích; source-span mismatch; corpus/index fingerprint lệch.

Parser/chunker/validator hiện tại chỉ `Code present`; code existence không mở gate C0.

## Phase 3 — LegalIR B0/B1/B2

Chạy E00–E04 trên cùng C0 fingerprint: BM25, BGE-M3 control, weighted fusion, RRF, cross-encoder. Log candidate Recall@K curve, zero/full-recall rates, official `recall`/`precision`, overlap/unique gold, chunk→document behavior và compute.

- **GO:** run tái lập được và bottleneck được xác định.
- **NO-GO:** score không ổn định/không giải thích được, encoding/index mismatch hoặc document deduplication sai.
- Candidate coverage cao nhưng final official recall thấp: ưu tiên aggregation/reranking/subset selection.
- Candidate coverage thấp và final gần candidate ceiling: ưu tiên retrieval/representation.

“Cao/thấp” là threshold working hypothesis, không phải fact hiện tại.

## Phase 4 — representation và chunk→document improvements

Chạy D03–D05 rồi E05–E06 với fixed downstream stack: retrieval-unit strategy, size/overlap, title/hierarchy enrichment và document aggregation. Tách chunk boundary, enrichment, candidate construction, aggregation và reranking.

- **GO:** gain lặp lại trên held-out/aggregate và target error category, không do duplicate/title leakage; corpus variant qua D06.
- **NO-GO:** chỉ tăng chunk score nhưng không tăng document outcome, hoặc representation gây source loss/truncation/regression.

## Phase 5 — reranker/hard negatives

Chạy E07 theo conservative negative curriculum sau label audit.

- **GO:** official scores/final subset cải thiện trên cùng candidate pool, đặc biệt F05/F11; false-negative audit chấp nhận được.
- **NO-GO:** candidate retrieval vẫn là bottleneck; labels không đủ; gain chỉ ở train/public tuning.

## Phase 6 — retriever adaptation

Chạy E08; DAPT/TAPT hoặc synthetic queries chỉ là conditional research candidates.

- **GO:** candidate coverage/unique gold tăng tại depth hữu ích và generalize qua split.
- **NO-GO:** chỉ đổi calibration, làm hỏng exact citation hoặc dùng negative đáng ngờ.

## Phase 7 — retrieval diversity

Chạy E09–E12: SPLADE, ColBERT, query variants và PRF. Original query luôn được giữ ở expansion branches.

- **GO:** unique gold/union recall bù latency/index cost và cải thiện đúng error category.
- **NO-GO:** overlap gần hoàn toàn, cùng gold misses, query drift hoặc compute tăng không tạo final gain.

## Phase 8 — distillation/pseudo-labeling

Chạy E13 khi teacher đã `Validated` và `Benchmarked`. Ablate hard labels, soft scores/margins và filtered pseudo-labeling.

- **GO:** student tăng retrieval quality ở cùng/thấp hơn inference cost; false-label audit đạt yêu cầu.
- **NO-GO:** sao chép teacher bias, confirmation loop hoặc confidence không calibrated.

## Phase 9 — alternative LegalIR formulations

Chạy E15 direct document-ID trước khi cân nhắc E16 generative retrieval.

- **GO:** recover unique gold, valid-ID rate cao và có ensemble value.
- **NO-GO:** memorization, unseen-document failure, catastrophic identifier hoặc cost không tương xứng.

Các hướng này không thay B2 reference system. E14 final subset calibration chạy sau khi B2 ranking ổn định; always-top-5 là control và cả official recall/precision đều phải báo.

## LegalQA track

### QA0 — early controls

Chạy closed-book khi scorer/data/generator fixed. Chạy gold-evidence oracle khi mapping đã verified.

- **GO:** control reproducible và error attribution có ý nghĩa.
- **NO-GO:** mapping gold mơ hồ, prompt/parser không fixed hoặc scorer reproduction sai.

### QA1 — after LegalIR B2 benchmark on validated corpus

So retrieve–rerank–generate với no-rerank RAG trên cùng canonical evidence records, generator/context policy và source-preserving evidence adapter.

- **GO:** selected evidence/official metric thay đổi đúng hypothesis.
- **NO-GO:** B2 chưa measurable, C0/D06 chưa đạt, comparison thay nhiều axis hoặc evidence trace thiếu.

### QA2 → QA3 → QA4

QA2 ablate span selection; QA3 ablate verifier; QA4 chỉ thay answer realization sau factual support. Mỗi bước giữ fixed component theo [experiment map](05_experiment_map.md).

- **GO:** addition cải thiện target diagnostic hoặc official metric mà không che regression quan trọng.
- **NO-GO:** metric gain đi kèm unsupported claims/dropped legal conditions, hoặc verifier/selector chưa được audit.

FiD, iterative RAG/IRCoT, Self-RAG/CRAG, PEFT, GraphRAG và joint IR–QA là later-stage research, không phải prerequisite của QA baseline.

## Cross-track gates

```text
source coverage/provenance fail              → preprocessing / corpus representation
candidate recall high + final recall low → aggregation / reranking / subset selection
candidate recall low  + final near ceiling → retrieval
oracle QA high + end-to-end low           → retrieval / evidence selection
oracle QA low                              → generator / reasoning / realization or mapping audit
```

## Dừng và quay lại

Dừng một family sau ít nhất một implementation đúng và một validation có attribution nếu nó không tạo unique evidence, gain không lặp lại, cost vượt budget hoặc error analysis cho thấy giải sai bottleneck. Ghi null/failed run vào [05 — Experiment map](05_experiment_map.md); không biến null result thành claim method vô dụng trên mọi setting.
