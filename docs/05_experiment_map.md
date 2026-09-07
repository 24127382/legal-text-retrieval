# 05 — Experiment map

## Quy tắc vận hành

`Control` là cấu hình tham chiếu; `independent variable` là yếu tố chủ động thay đổi. Mỗi experiment chỉ đổi **một major research axis**. Trạng thái hợp lệ: `Blocked`, `Ready`, `Running`, `Completed`, `Rejected`; hiện tại mọi experiment đều chưa chạy.

Trước E00 phải hoàn tất D00: xác minh scorer/rules, data split, gold distribution và label completeness signals theo [`04_evaluation_and_diagnostics.md`](04_evaluation_and_diagnostics.md).

## Ma trận LegalIR

| ID | Hypothesis | Change from control | Fixed components | Independent variable | Primary metric | Expected signal | Failure interpretation | Compute | Status |
|---|---|---|---|---|---|---|---|---:|---|
| D00 | Protocol đúng tạo ceiling/metric đáng tin | Phân tích data/scorer, không đổi model | Raw data version | Scorer + gold audit | Reproduction + `|G_q|` stats | Official/local score khớp | Không khớp: dừng model experiments | L | `Blocked`: cần data/rules |
| E00 | BM25 tạo lexical floor mạnh | First lexical system | Split, doc aggregation control | Tokenization + BM25 params | candidate R@K, final R@5 | Mạnh F01/F02 | Thấp: preprocessing/index unit có vấn đề | L–M | `Ready` sau D00 |
| E01 | Current BGE-M3 tăng paraphrase coverage | BM25 → dense | Split, aggregation, final-k | Retriever family | candidate R@K | Recover F03/F04 unique gold | Không hơn/không bổ sung: inspect encoding/domain gap | M–H | `Ready` sau D00 |
| E02 | Alpha fusion tận dụng complementary scores | Union E00+E01 + linear fusion | Candidate depths, aggregation | Normalization + α | union R@K, final R@5 | Gain với unique gold giữ lại | Gain không có: score calibration/error overlap | M | `Blocked` E00/E01 |
| E03 | RRF robust hơn khi score scales lệch | E02 fusion → RRF | Same candidate lists/depths | Fusion rule + RRF `k` | final R@5 | Gain ổn định không cần raw calibration | Thua E02: magnitude có ích hoặc `k` sai | M | `Blocked` E00/E01 |
| E04 | Cross-encoder sửa misordering khi pool đủ gold | Best E02/E03 + CE | Exact candidate pool | Reranker/model/depth | final R@5 vs pool ceiling | Gap candidate→final giảm | Không gain: pool thấp, truncation hoặc domain mismatch | H | `Blocked` best hybrid |
| E05 | Title context sửa title-dependent misses | Enrich indexed/scored text | Best B2, chunk boundaries | Title/parent enrichment | candidate R@K + F07 | F07 gain, limited regression | Regression: noisy/duplicated title or truncation | M–H | `Blocked` B2 |
| E06 | Aggregation ảnh hưởng document ranking độc lập | max → mean/weighted/rank/learned | Same chunk candidates/scores | Aggregation rule | doc candidate R@K, final R@5 | F08 gain | No gain: chunk retrieval itself is bottleneck | M | `Blocked` B2 |
| E07 | Conservative hard negatives improve reranker | Fine-tune CE | Frozen retrievers/pool | Negative curriculum | final R@5 + F05/F11 | Similar-law ordering gain | Regression/F12: false negatives or overfit | H | `Blocked` label audit |
| E08 | Dense hard-negative tuning increases coverage | Fine-tune dense | Same B2 reranker/fusion eval | Training negatives/loss | candidate R@K | Unique gold/F03–F05 gain | Final only/no candidate gain: representation not improved | VH | `Blocked` E07/data |
| E09 | SPLADE adds useful sparse-semantic diversity | Add SPLADE branch | B2 control, same eval | Retriever branch | unique gold, union R@K | Recover beyond BM25+dense | High overlap/no unique gold: reject compute | H–VH | `Blocked` B2 |
| E10 | ColBERT reduces single-vector bottleneck | Add ColBERT branch | B2 control | Late-interaction retriever | unique gold, union R@K | Fine-grained F05 gain | No complement or excessive cost: no-go | VH | `Blocked` B2 |
| E11 | Original + multi-query/legal rewrite expands coverage | Add query variants, retain original | Retriever/index/fusion | Query diversification | candidate R@K, drift rate | Unique F03/F04/F09 gold | Regressions: query drift/noise | H | `Blocked` B2 |
| E12 | PRF corpus terms outperform pure generative rewrite on some mismatches | Original + RM3-style branch | First retrieval and B2 | Feedback docs/terms/weight | candidate R@K, drift audit | Corpus-grounded unique gold | Initial pool wrong → drift; keep auxiliary only | M–H | `Blocked` B2 |
| E13 | Teacher soft labels improve cheaper retriever | CE teacher → student | Corpus/split/teacher checkpoint | Soft-label/distillation loss | candidate R@K, latency | Student gain at same inference cost | Teacher bias/false pseudo-labels | VH | `Blocked` validated teacher |
| E14 | Calibrated decision improves tie-break without harming Recall | Always-5 → threshold/margin/probability/adaptive-k | Same final ranking | Decision rule | Recall + official Precision | Precision gain with negligible Recall loss | Recall loss: retain always-5 | L–M | `Blocked` scorer/B2 |
| E15 | Direct doc-ID model adds corpus-specific diversity | Add learned ID scoring branch | Same split/eval | Alternative formulation | unique gold, final R@5 | Ensemble diversity on fixed corpus | Memorization/unseen-doc failure | H–VH | `Blocked` mature B2 |
| E16 | Generative retrieval can optimize IDs directly | DSI/NCI prototype | Same IDs/split | Generative index | Recall@K, invalid-ID rate | Complementary valid IDs | Catastrophic IDs/cost/generalization | VH | `Blocked` low priority |

Candidate depths 10/20/50/100/200 và BM25/dense top 100 là working hypotheses. Tune theo candidate-recall curve và compute, không hard-code như sự thật.

## Mandatory comparison fields

Mỗi row có nhiều retriever phải ghi:

```text
overlap(A, B)
unique_gold(A)
unique_gold(B)
recall(union(A, B))
incremental latency / memory / index size
```

Mỗi training experiment phải ghi random → semi-hard → hard → teacher-filtered progression, false-negative audit và label provenance.

## Run log

Thêm record mới bên dưới, không sửa record cũ.

### Template

- **Run ID / date:**
- **Experiment / hypothesis:**
- **Commit, config, split fingerprint, seed:**
- **Control / change / fixed components / independent variable:**
- **Candidate Recall@10/20/50/100/200:**
- **Final Recall@5 / Precision / MRR/nDCG diagnostics:**
- **Overlap / unique gold / union recall:**
- **Gold distribution ceiling applied:**
- **F01–F12 gains and regressions:**
- **Compute / latency / index size:**
- **Unexpected behavior / false-negative suspicions:**
- **Decision:** GO / NO-GO / repeat; next experiment and reason.

_Chưa có run được ghi nhận trên branch này._
