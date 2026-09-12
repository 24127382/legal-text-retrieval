# 05 — Experiment map

## Quy tắc vận hành

`Control` là cấu hình tham chiếu; `independent variable` là yếu tố chủ động thay đổi. Trạng thái nghiên cứu dùng thống nhất: `Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate`, `Speculative`. Code/prototype tồn tại không chứng minh experiment đã chạy.

> **One major research axis per experiment.**

Valid:

```text
same corpus + same BM25 + different chunk size
same corpus + different retriever + same aggregation
```

Invalid cho causal attribution:

```text
new parser + new chunking + new embedding model + new reranker
```

Mọi run phải ghi control, independent variable và fixed components. Khi so LegalIR algorithm, corpus fingerprint fixed; khi so corpus representation, downstream retrieval stack fixed; khi so reranker, candidate pool fixed.

Scoring contract nằm tại [04 — Evaluation và diagnostics](04_evaluation_and_diagnostics.md). Hiện không có result nào được ghi nhận trong document này.

## P00 — protocol/scorer verification

| Phần việc | Trạng thái | Evidence hiện có / artifact còn thiếu |
|---|---|---|
| Official LegalIR scorer contract | `Validated` against organizer artifact | Scoring path đã được inspect; executable regression cases và scorer hash vẫn `Planned`. |
| Official LegalQA scorer contract | `Validated` against organizer artifact | Scoring/tokenizer path đã được inspect; executable regression cases và runtime hash vẫn `Planned`. |
| Submission schema/key behavior | `Validated` against organizer artifact | Executable valid/invalid submission fixtures vẫn `Planned`. |
| Runtime/package reproduction | `Planned` | Scorer environment, NLTK version/resources, deterministic test outputs. |
| Organizer scorer regression pack | `Planned` | Expected outputs, scorer artifact/hash và package/runtime fingerprint. |

P00 tách immutable scoring truth khỏi data/corpus audit. Inspect scorer source không hoàn thành D00 và inspect local data không thay đổi scorer contract.

## Data & Corpus experiments D00–D06

Toàn bộ series theo contract ở [00 — Data contract và preprocessing](00_data_contract_and_preprocessing.md). Snapshot inspection hiện có không được ghi như experimental result; mọi experiment dưới đây đang `Planned`.

### D00 — raw data/schema/split audit

- **Hypothesis:** available competition data có thể map sang canonical records mà không silent loss hoặc ID corruption.
- **Control:** immutable raw files + declared schema expectations; **independent variable:** không có model, chỉ audit rules/exception policy.
- **Fixed components:** raw bytes, task semantics, scorer artifacts.
- **Data/corpus diagnostics:** schema/type/nullability violations; duplicate/missing IDs; null/empty values; question-representation audit; exact/near-duplicate groups; task-aware passage/document overlap; gold-document distribution/maximum-5 ceiling; label-completeness signals. Cross-task report phải tách sample-ID overlap, exact/canonical question overlap count/rate, one-to-one/one-to-many mapping, gold document ID resolution, QA evidence granularity và competition-rule permission.
- **Local split artifact:** deterministic immutable manifest với explicit sample/group IDs, data/manifest fingerprint, fixed seed khi có randomness, duplicate-group isolation, cross-task pair grouping khi có information flow và task-label distribution report; không khóa tỷ lệ trước khi justified.
- **Downstream LegalIR diagnostics:** chưa optimize retrieval; chỉ xác nhận gold IDs có thể resolve về corpus khi expected.
- **Expected signal:** complete manifest, explicit exceptions, zero silent loss/ID remap.
- **Failure interpretation:** raw ambiguity/schema drift/missing source dependency; block C0 thay vì tự sửa hoặc skip.
- **Dependency/status:** local data availability; `Planned`.

### D01 — minimal normalization contract

- **Hypothesis:** conservative normalization loại representation noise mà không phá legal signals hoặc source identity.
- **Control:** raw source text; **independent variable:** một normalization rule/policy mỗi comparison.
- **Fixed components:** raw manifest, document IDs, parser/chunker/retriever tắt hoặc giữ fixed cho downstream check.
- **Data/corpus diagnostics:** transform counts; reversible/diff samples; punctuation/numbering/`Điều`–`Khoản`–`Điểm` preservation; empty-text delta; source fingerprint mapping.
- **Downstream LegalIR diagnostics:** khi cần, fixed B0 trên cùng retrieval-unit policy để phát hiện regression exact citation/terminology.
- **Expected signal:** noise giảm, legal text/source coverage và identifiers giữ nguyên.
- **Failure interpretation:** rule quá aggressive hoặc artifact chưa được chứng minh là noise; reject/limit rule.
- **Dependency/status:** D00 manifest; `Planned`.

### D02 — legal structure parsing QC

- **Hypothesis:** parser configuration nhận diện structural boundaries đủ đáng tin để dùng làm derived metadata/chunk boundaries.
- **Control:** canonical source text + manual/curated sample; **independent variable:** một parsing rule/config hoặc fallback policy.
- **Fixed components:** D01 normalization, source coordinate system; chưa optimize retrieval.
- **Data/corpus diagnostics:** success/failure, hierarchy distributions, malformed/impossible transitions, parent leakage, overlapping/duplicate/uncovered spans, source coverage, stratified manual inspection.
- **Downstream LegalIR diagnostics:** không bắt buộc; nếu chạy chỉ là fixed sanity check, không dùng để che parser errors.
- **Expected signal:** boundaries/provenance tái lập, failure được flag, không silent skip.
- **Failure interpretation:** source heterogeneity/rule ambiguity; fallback về coarser auditable unit thay vì gắn `Validated`.
- **Dependency/status:** D00–D01; parser prototype `Code present`, experiment `Planned`.

### D03 — retrieval-unit / chunking strategy

- **Hypothesis:** structural granularity thay đổi evidence availability và document-level retrieval outcome.
- **Control:** C0 unit policy; **independent variable:** một boundary strategy, ví dụ article-level vs clause-level vs structure-aware bounded chunks.
- **Fixed components:** source/normalization/parser version, enrichment policy, fixed B0 retriever/tokenization/aggregation/final rule.
- **Data/corpus diagnostics:** chunks/document, source coverage, boundaries crossed, token lengths, duplicate/overlap/truncation rate, provenance validity.
- **Downstream LegalIR diagnostics:** candidate Recall@K, zero/full-recall rate, official R/P, F01/F07/F08/F10 và compute/index delta.
- **Expected signal:** target failures cải thiện mà integrity/provenance không regression.
- **Failure interpretation:** wrong granularity hoặc aggregation/context budget trở thành bottleneck; không suy ra parser đúng/sai chỉ từ retrieval score.
- **Dependency/status:** validated C0 gate + B0 benchmark; `Planned`.

### D04 — chunk size / overlap

- **Hypothesis:** size/overlap policy trade off context completeness, duplication và truncation.
- **Control:** chosen structural policy; **independent variable:** token/size bound hoặc overlap, một loại mỗi comparison.
- **Fixed components:** source/normalization/parser, structural boundary policy, enrichment, fixed B0 stack.
- **Data/corpus diagnostics:** token lengths per tokenizer, source coverage, overlap distribution, duplicated chunk rate, chunks/document, truncation, index cost.
- **Downstream LegalIR diagnostics:** candidate Recall@K, unique gold, official R/P, aggregation sensitivity và latency.
- **Expected signal:** coverage tăng tại useful depth với duplicate/truncation/cost trong preregistered tolerance.
- **Failure interpretation:** overlap chỉ lặp score/evidence hoặc size làm loãng/cắt legal condition.
- **Dependency/status:** D03 control + fixed B0; `Planned`.

### D05 — hierarchy/title enrichment

- **Hypothesis:** parent/title context trong `retrieval_text` giải scope misses mà không làm sai source evidence.
- **Control:** identical `source_text` và chunk boundaries, enrichment off; **independent variable:** một metadata enrichment/serialization policy.
- **Fixed components:** corpus source spans, chunk IDs/boundaries, retriever/tokenizer/aggregation/final rule.
- **Data/corpus diagnostics:** enrichment coverage, `source_text`/`retrieval_text` expansion ratio, missing-metadata behavior, tokenizer-specific truncation delta.
- **Downstream LegalIR diagnostics:** candidate Recall@K, official R/P, F07, gains/regressions theo enriched field.
- **Expected signal:** scope-dependent recovery without source corruption or broad truncation regression.
- **Failure interpretation:** noisy/duplicated metadata, score bias hoặc enrichment exceeds context budget.
- **Dependency/status:** C0 + fixed B0; `Planned`.

### D06 — provenance and corpus/index integrity

#### D06a — canonical corpus integrity

- **Hypothesis:** identical raw inputs + preprocessing config regenerate cùng canonical corpus và provenance mapping, không silent loss.
- **Control:** recorded input/config/manifests/fingerprints; **independent variable:** regeneration environment, không đổi research method.
- **Fixed components:** raw bytes, preprocessing config/code revision, serialization contract.
- **Data/corpus diagnostics:** unique document/chunk IDs; valid chunk→document mapping; source-slice equality/coverage; no orphan/empty/unexplained duplicate; deterministic IDs; no silent loss/skip/truncation; input/config/corpus fingerprints.
- **Expected signal:** zero unexplained mismatch và reproducible canonical mapping.
- **Failure interpretation:** nondeterministic ID/order, provenance corruption hoặc corpus drift; block C0.
- **Dependency/status:** D00–D02; `Planned`. D06a success cho phép freeze C0; không cần index tồn tại.

#### D06b — index ↔ corpus alignment

- **Hypothesis:** index/evaluation load đúng D06a-validated corpus manifest và compatible encoder/index configuration.
- **Control:** C0/corpus-variant manifest + recorded index build config; **independent variable:** build/reload environment, không đổi retriever method.
- **Fixed components:** corpus bytes/fingerprint, manifest IDs, encoder/tokenizer revision và index serialization contract.
- **Diagnostics:** `index item count ↔ manifest item count ↔ chunk/document IDs ↔ corpus fingerprint ↔ index fingerprint`; missing/extra IDs; ordering mismatch khi relevant; stale/foreign-corpus index; incompatible encoder/index config. Identical-query smoke test hoặc ranking checksum chỉ phát hiện mismatch, không phải benchmark claim.
- **Expected signal:** zero unexplained mismatch; load-time alignment reproducible.
- **Failure interpretation:** stale index, wrong corpus, missing IDs, nondeterministic ordering hoặc incompatible config; block retriever benchmark nhưng không block source-corpus creation.
- **Dependency/status:** build index sau C0/D06a; `Planned`. Mỗi index/corpus pair phải qua D06b trước benchmark.

`C0` được freeze từ một policy đơn giản sau D00–D02 và D06a. Sau đó build B0 index, chạy D06b, rồi mới benchmark B0. D03–D05 là controlled representation ablations sau khi có fixed B0; mỗi corpus variant đi qua `D06a → build index → D06b → benchmark`.

## Ma trận LegalIR E00–E16

`Official R/P` dưới đây là `recall`/`precision` đúng theo organizer scorer, không phải giả định priority. Candidate R@K, MRR và nDCG là diagnostics. Trừ experiment Data & Corpus được khai báo riêng, mọi LegalIR row giữ fixed C0 manifest/corpus fingerprint đã qua D06a và chỉ benchmark trên index đã qua D06b.

| ID | Hypothesis | Control → independent variable | Fixed components | Official metrics + diagnostics | Expected signal | Failure interpretation | Dependencies / status |
|---|---|---|---|---|---|---|---|
| E00 | BM25 tạo lexical floor hữu ích | No retriever → versioned `retrieval_query` tokenization/BM25 parameters | C0 corpus/split/fingerprint, `canonical_question`, document mapping, aggregation/final rule | Official R/P; candidate R@10/20/50/100/200; F01/F02 | Exact citation/terminology coverage | Low coverage: inspect representation/index unit through a separate D experiment | P00 + C0/D06a + BM25 index/D06b; `Planned` |
| E01 | BGE-M3 dense bổ sung paraphrase coverage | E00 → retriever family | C0 corpus/split/fingerprint, `canonical_question`, mapping, aggregation/final rule | Official R/P; candidate R@K; unique gold vs BM25 | F03/F04 unique recovery | No gain/complement: encoding/domain gap or redundant errors | E00 + dense index/D06b; dense prototype `Code present`, experiment `Planned` |
| E02 | Weighted fusion giữ complementary candidates | Union E00/E01 → normalization and α | Same lists/depths, aggregation/final rule | Official R/P; union R@K; overlap/unique gold | Unique gold retained into final subset | No gain: calibration/aggregation/error overlap | E00/E01; `Planned` |
| E03 | RRF robust hơn khi score scales lệch | E02 → fusion rule and RRF `k` | Exact candidate lists/depths | Official R/P; union R@K; paired delta | Stable gain without raw calibration | Loss: magnitude useful or `k` unsuitable | E00/E01; `Planned` |
| E04 | Cross-encoder fixes misordering when pool has gold | Best E02/E03 → CE model/depth | Exact candidate pool | Official R/P; candidate-ceiling gap; F05/F11 | Gap pool→final shrinks | No gain: low pool ceiling, truncation or domain mismatch | Hybrid benchmark; `Planned` |
| E05 | D05 enrichment candidate còn hiệu quả trên strong stack | B2 on unenriched corpus → D05-selected `retrieval_text` enrichment | `source_text`, split, chunk IDs/boundaries, B2 downstream stack | Official R/P; candidate R@K; F07; expansion/truncation | F07 gain with limited regression | Noise, duplicated title, leakage or truncation | D05 + B2; `Planned` |
| E06 | Aggregation independently changes document ranking | Max → mean/weighted/rank/learned rule | Same chunk hits/scores and reranker scope | Official R/P; document R@K; F08 | Gold documents move up without new chunks | No gain: chunk retrieval itself bottleneck | B2; `Planned` |
| E07 | Conservative hard negatives improve CE | Frozen CE → negative curriculum | Retriever/candidate pool/split | Official R/P; candidate ceiling; F05/F11/F12 audit | Better similar-law ordering | Regression: false negatives/overfit | Label audit; `Planned` |
| E08 | Dense tuning improves coverage | Frozen dense → loss/negative curriculum | B2 evaluation stack | Official R/P; candidate R@K; unique gold | F03–F05 candidate gain | Final-only gain/no candidate gain: representation claim unsupported | E07/data; `Planned` |
| E09 | SPLADE adds sparse-semantic diversity | B2 → add SPLADE branch | Same evaluation/downstream stack | Official R/P; unique gold; union R@K; cost | Recovery beyond BM25+dense | High overlap/no unique gold: reject extra cost | B2; `Planned` |
| E10 | ColBERT reduces single-vector bottleneck | B2 → late-interaction branch | Same evaluation/downstream stack | Official R/P; unique gold; union R@K; cost | Fine-grained F05 recovery | No complement or excessive cost | B2; `Planned` |
| E11 | Original + query variants expands coverage | Original → multi-query/legal rewrite while retaining original | Retriever/index/fusion | Official R/P; candidate R@K; unique gold; drift rate | F03/F04/F09 recovery | Query drift/noise/regression | B2; `Planned` |
| E12 | Corpus-grounded PRF helps vocabulary mismatch | Original → RM3-style branch | Initial retrieval and B2 stack | Official R/P; candidate R@K; unique gold; drift audit | F04 recovery grounded in corpus | Wrong first pass causes feedback drift | B2; `Planned` |
| E13 | Teacher soft labels improve cheaper retriever | Hard-label student → distillation/pseudo-label loss | Corpus/split/validated teacher | Official R/P; candidate R@K; latency | Better quality at same/lower inference cost | Teacher bias/confirmation loop | Validated teacher; `Planned` |
| E14 | Calibrated subset improves P without unacceptable R loss | Always-top-5 → threshold/margin/probability/adaptive-k | Same final document ranking | Both official R/P; chosen-k distribution; calibration | Explicit Pareto improvement/trade-off | Recall loss beyond preregistered tolerance: keep control | B2 + scorer tests; `Planned` |
| E15 | Direct document-ID scoring adds diversity | B2 → learned ID-scoring branch | Split/evaluation | Official R/P; unique gold; unseen-doc behavior | Ensemble diversity on fixed corpus | Memorization/generalization failure | Mature B2; `Planned` |
| E16 | Generative retrieval can produce useful ID candidates | B2 → DSI/NCI-style generative index | IDs/split/evaluation | Official R/P; candidate R@K; invalid-ID rate; cost | Complementary valid IDs | Catastrophic IDs/cost/generalization | Mature B2; `Planned`, low priority |

Candidate depths 10/20/50/100/200, BM25 top-100, dense top-100 và cross-encoder depth 50–200 là working hypotheses. Tune trên validation và log compute; không biến thành dataset fact.

## Ma trận LegalQA QA0–QA4

Mọi run dùng submission adapter chỉ emit `{sample_id: {"answer": <text>}}`. Evidence/provenance được lưu trong internal artifact, không nối tự động vào answer.

### G0 — frozen QA generator control

**Mục đích:** tạo generator control ổn định cho causal attribution, không tìm globally best LLM và không yêu cầu model sweep. **Status:** `Planned`.

G0 artifact phải freeze: provider/model identifier và exact model revision nếu có; tokenizer revision nếu applicable; prompt template; system/instruction prompt; decoding parameters; `temperature`; `top-p`/`top-k` nếu dùng; max output tokens; context budget; evidence serialization; answer extraction/parser; retry policy; random seed khi được hỗ trợ; API/runtime/package version. Nếu provider không công bố exact revision, ghi model identifier, access date và runtime metadata chính xác nhất có thể.

Trước khi QA0 được gọi `Benchmarked`, G0 phải có sanity/reproducibility report: prompt/render/parser pass trên fixed fixtures, output/schema hợp lệ, retry behavior được kiểm tra, và repeated deterministic hoặc variance-characterization runs phù hợp API. QA0 dùng `G0 + no evidence` so với `G0 + verified gold-document/passage/span condition`. QA1–QA4 giữ G0 hoặc một declared successor cố định trừ khi generator choice chính là independent variable; đổi `retriever + generator` trong cùng comparison làm mất attribution.

| ID | Hypothesis | Control | Independent variable | Fixed components | Official metric | Internal diagnostics | Expected signal | Failure interpretation | Dependencies / status |
|---|---|---|---|---|---|---|---|---|---|
| QA0 | Controls tách giá trị của evidence khỏi generator | G0 closed-book; G0 + oracle condition nếu mapping reliable/allowed | Evidence condition: none vs verified gold document/passage/span | G0, `generator_question`, output adapter; oracle evidence adapter fixed | `rouge`, `meteor` | Mapping coverage/granularity; support rate; answer length | Valid oracle evidence improves grounded answer over closed-book | No gap: G0/prompt ceiling, weak mapping, or task not evidence-limited; không suy ra retrieval tốt | P00 + QA data + G0; oracle conditional on mapping and rule audit; `Planned` |
| QA1 | Retrieve–rerank–generate improves over no-rerank RAG | Same retriever + G0 without reranking | Reranking and evidence order/subset | Canonical evidence records, G0, `generator_question`, context budget, submission adapter | `rouge`, `meteor` | Candidate/evidence coverage; selected support; retrieval/selection/generation error split | Better selected evidence and official scores | No gain: coverage ceiling, reranker mismatch, generator insensitive or metric variance | LegalIR B2 benchmark on C0/index D06b + G0; `Planned` |
| QA2 | Extract-then-generate reduces distractor noise | QA1 full-source-chunk context | Evidence selector/extracted source spans | Retrieved canonical records, source-preserving evidence, G0, budget | `rouge`, `meteor` | Span coverage/precision if labels; claim support; omitted-condition errors | Higher support/conciseness without evidence loss | Selector drops conditions or adds no value over chunks | QA1 + fixed G0; `Planned` |
| QA3 | Verifier reduces unsupported claims | QA2 without verifier | Verification/action policy | Evidence, G0 candidates, submission formatting | `rouge`, `meteor` | Claim support; unsupported/abstention rate; verifier calibration/manual audit | Fewer unsupported claims with controlled official-score trade-off | Verifier domain mismatch, over-deletion or false confidence | QA2 + fixed G0 + verifier validation set; `Planned` |
| QA4 | Metric-aware realization improves lexical alignment after grounding | Grounded QA3 answer realization | Concision/canonical wording/length policy | Evidence, claims, verifier result, G0 facts | `rouge`, `meteor` | Support invariance; answer length; edit/error audit | Official gain with unchanged factual support | Metric gaming, dropped condition or support regression | QA3 + fixed G0; `Planned` |

Không có row nào chứa result. “Expected signal” là prediction của hypothesis, không phải kết quả đã quan sát.

## Mandatory comparison fields

Retriever comparison phải ghi C0/corpus fingerprint, candidate overlap, unique gold mỗi nhánh, union recall, latency/memory/index delta. Corpus comparison phải ghi input/config/corpus/index fingerprints, manifest consistency và data/corpus diagnostics. Training run phải ghi negative provenance, random → semi-hard → hard → teacher-filtered progression khi áp dụng và false-negative audit.

## Unified run log

Thêm record mới; không sửa record cũ. Chọn phần LegalIR, LegalQA hoặc cả hai theo task.

### Template

- **Run ID / date / task:**
- **Experiment / preregistered hypothesis:**
- **Research status:** `Benchmarked` chỉ khi artifact dưới đây đầy đủ.
- **Commit / config / input data fingerprint / immutable split manifest+fingerprint / seed:**
- **Question representation / canonical-to-retrieval transform and variant provenance:**
- **Preprocessing config / canonical corpus fingerprint / document and chunk manifests:**
- **Index fingerprint / item-count and chunk-ID consistency / provenance validation:**
- **Scorer artifact/hash / runtime package versions:**
- **G0 or declared generator-control artifact / revision / prompt / decoding / parser / retry metadata:**
- **Control / independent variable / fixed components:**
- **Submission schema validation:**
- **LegalIR official `recall` / `precision`:**
- **LegalIR candidate Recall@10/20/50/100/200, zero/full-recall rates:**
- **LegalIR overlap / unique gold / union recall / chunk→document diagnostics:**
- **LegalQA official `rouge` / `meteor`:**
- **LegalQA evidence coverage / claim support / citation validity / answer length:**
- **Gold-distribution ceiling or gold-document/passage/span mapping used + permission artifact:**
- **Error categories, gains/regressions, unexpected behavior:**
- **Compute / latency / memory / index size:**
- **Artifacts:** predictions, logs, checkpoints/configs, environment fingerprint.
- **Decision:** GO / NO-GO / repeat; next experiment and reason.

_Chưa có run được ghi nhận trên branch này._
