# 05 — Experiment map

## Quy tắc vận hành

`Control` là cấu hình tham chiếu; `independent variable` là yếu tố chủ động thay đổi. Mỗi experiment đổi một major research axis. Trạng thái nghiên cứu dùng thống nhất: `Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate`, `Speculative`. Code/prototype tồn tại không chứng minh experiment đã chạy.

Scoring contract nằm tại [04 — Evaluation và diagnostics](04_evaluation_and_diagnostics.md). Hiện không có result nào được ghi nhận trong document này.

## D00 — protocol và data verification

| Phần việc | Trạng thái | Evidence hiện có / artifact còn thiếu |
|---|---|---|
| Official LegalIR scorer contract | `Validated` against organizer artifact | Scoring path đã được inspect; executable regression cases và scorer hash vẫn `Planned`. |
| Official LegalQA scorer contract | `Validated` against organizer artifact | Scoring/tokenizer path đã được inspect; executable regression cases và runtime hash vẫn `Planned`. |
| Submission/data key schema trên file hiện có | `Validated` by inspection | Bốn JSON hiện có đã được inspect; automated schema check/fingerprint vẫn `Planned`. |
| Split/leakage audit | `Planned` | Split manifest, duplicate/near-duplicate policy. |
| Gold-document distribution/ceiling | `Planned` | `|G_q|` statistics và macro maximum-5 recall ceiling. |
| Label-completeness signals | `Planned` | Sampling protocol, ambiguous/unlabelled policy. |
| Gold-evidence mapping cho LegalQA | `Planned` | Mapping coverage/quality; nếu không có, oracle QA được đánh dấu unavailable. |
| Runtime/package reproduction | `Planned` | Scorer environment, NLTK version/resources, deterministic test outputs. |

D00 chưa hoàn tất toàn bộ. Phần **official scorer contract available** đã được giải quyết; data/split/gold questions vẫn mở.

## Ma trận LegalIR E00–E16

`Official R/P` dưới đây là `recall`/`precision` đúng theo organizer scorer, không phải giả định priority. Candidate R@K, MRR và nDCG là diagnostics.

| ID | Hypothesis | Control → independent variable | Fixed components | Official metrics + diagnostics | Expected signal | Failure interpretation | Dependencies / status |
|---|---|---|---|---|---|---|---|
| E00 | BM25 tạo lexical floor hữu ích | No retriever → tokenization/BM25 parameters | Split, document mapping, aggregation/final rule | Official R/P; candidate R@10/20/50/100/200; F01/F02 | Exact citation/terminology coverage | Low coverage: inspect preprocessing/index unit | Data D00; `Planned` |
| E01 | BGE-M3 dense bổ sung paraphrase coverage | E00 → retriever family | Split, mapping, aggregation/final rule | Official R/P; candidate R@K; unique gold vs BM25 | F03/F04 unique recovery | No gain/complement: encoding/domain gap or redundant errors | Data D00; dense prototype `Code present`, experiment `Planned` |
| E02 | Weighted fusion giữ complementary candidates | Union E00/E01 → normalization and α | Same lists/depths, aggregation/final rule | Official R/P; union R@K; overlap/unique gold | Unique gold retained into final subset | No gain: calibration/aggregation/error overlap | E00/E01; `Planned` |
| E03 | RRF robust hơn khi score scales lệch | E02 → fusion rule and RRF `k` | Exact candidate lists/depths | Official R/P; union R@K; paired delta | Stable gain without raw calibration | Loss: magnitude useful or `k` unsuitable | E00/E01; `Planned` |
| E04 | Cross-encoder fixes misordering when pool has gold | Best E02/E03 → CE model/depth | Exact candidate pool | Official R/P; candidate-ceiling gap; F05/F11 | Gap pool→final shrinks | No gain: low pool ceiling, truncation or domain mismatch | Hybrid benchmark; `Planned` |
| E05 | Title/parent context fixes scope misses | B2 → enrichment representation | Split, chunk boundaries, downstream stack | Official R/P; candidate R@K; F07; truncation | F07 gain with limited regression | Noise, duplicated title, leakage or truncation | B2; `Planned` |
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

| ID | Hypothesis | Control | Independent variable | Fixed components | Official metric | Internal diagnostics | Expected signal | Failure interpretation | Dependencies / status |
|---|---|---|---|---|---|---|---|---|---|
| QA0 | Controls tách giá trị của evidence khỏi generator | Closed-book; gold-evidence control nếu mapping reliable | Evidence condition: none vs gold | Same generator, prompt, decoding, parser | `rouge`, `meteor` | Evidence coverage if mapping exists; support rate; answer length | Reliable gold evidence improves grounded answer over closed-book | No gap: generator/prompt ceiling, weak mapping, or task not evidence-limited; không suy ra retrieval tốt | Scorer/data; oracle conditional on verified gold mapping; `Planned` |
| QA1 | Retrieve–rerank–generate improves over no-rerank RAG | Same retriever/generator without reranking | Reranking and evidence order/subset | Generator, prompt, decoding, context budget, submission adapter | `rouge`, `meteor` | Candidate/evidence coverage; selected support; retrieval/selection/generation error split | Better selected evidence and official scores | No gain: coverage ceiling, reranker mismatch, generator insensitive or metric variance | LegalIR B2 benchmark; `Planned` |
| QA2 | Extract-then-generate reduces distractor noise | QA1 full-chunk context | Evidence selector/extracted spans | Retrieved documents, generator, prompt, decoding, budget | `rouge`, `meteor` | Span coverage/precision if labels; claim support; omitted-condition errors | Higher support/conciseness without evidence loss | Selector drops conditions or adds no value over chunks | QA1; `Planned` |
| QA3 | Verifier reduces unsupported claims | QA2 without verifier | Verification/action policy | Evidence, generator candidates, submission formatting | `rouge`, `meteor` | Claim support; unsupported/abstention rate; verifier calibration/manual audit | Fewer unsupported claims with controlled official-score trade-off | Verifier domain mismatch, over-deletion or false confidence | QA2 + verifier validation set; `Planned` |
| QA4 | Metric-aware realization improves lexical alignment after grounding | Grounded QA3 answer realization | Concision/canonical wording/length policy | Evidence, claims, verifier result, generator facts | `rouge`, `meteor` | Support invariance; answer length; edit/error audit | Official gain with unchanged factual support | Metric gaming, dropped condition or support regression | QA3; `Planned` |

Không có row nào chứa result. “Expected signal” là prediction của hypothesis, không phải kết quả đã quan sát.

## Mandatory comparison fields

Retriever comparison phải ghi candidate overlap, unique gold mỗi nhánh, union recall, latency/memory/index delta. Training run phải ghi negative provenance, random → semi-hard → hard → teacher-filtered progression khi áp dụng và false-negative audit.

## Unified run log

Thêm record mới; không sửa record cũ. Chọn phần LegalIR, LegalQA hoặc cả hai theo task.

### Template

- **Run ID / date / task:**
- **Experiment / preregistered hypothesis:**
- **Research status:** `Benchmarked` chỉ khi artifact dưới đây đầy đủ.
- **Commit / config / data and split fingerprint / seed:**
- **Scorer artifact/hash / runtime package versions:**
- **Control / independent variable / fixed components:**
- **Submission schema validation:**
- **LegalIR official `recall` / `precision`:**
- **LegalIR candidate Recall@10/20/50/100/200, zero/full-recall rates:**
- **LegalIR overlap / unique gold / union recall / chunk→document diagnostics:**
- **LegalQA official `rouge` / `meteor`:**
- **LegalQA evidence coverage / claim support / citation validity / answer length:**
- **Gold-distribution ceiling or gold-evidence mapping used:**
- **Error categories, gains/regressions, unexpected behavior:**
- **Compute / latency / memory / index size:**
- **Artifacts:** predictions, logs, checkpoints/configs, environment fingerprint.
- **Decision:** GO / NO-GO / repeat; next experiment and reason.

_Chưa có run được ghi nhận trên branch này._
