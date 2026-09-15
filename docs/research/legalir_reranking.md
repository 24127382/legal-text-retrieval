# LegalIR reranking research history

Detailed evidence for frozen cross-encoder reranking, final-output-size calibration, and Dense→CE validation. Historical states are retained and marked by their original context; the current validated state is summarized in [the research state index](../research_log.md).

## Kaggle offline execution workflow

Từ 2026-09-13, executable research experiments, preprocessing và inference được duy trì dưới dạng standalone Kaggle notebooks chạy với Internet disabled. Mỗi notebook inline implementation và experiment-level sanity checks, chỉ dùng package có sẵn hoặc resource được attach rõ ràng qua Kaggle Input, và không phụ thuộc vào repository `src/`. Các local Python research modules và test suite cũ được gỡ để tránh hai implementation authority song song; historical entries ở trên vẫn mô tả đúng code và evidence tại thời điểm từng run.

## Zero-shot cross-encoder reranking on fixed BM25 candidates

### Question

Can a zero-shot cross-encoder improve final document ranking while the BM25 candidate set and all upstream controls remain fixed?

### Fixed controls

- Corpus: 8.532 documents, 199.816 fixed character-window chunks, `chunk_size=2000`, `overlap=200`.
- Retrieval: `bm25s==0.3.11`, Lucene BM25, `k1=1.5`, `b=0.75`, top 2.000 BM25 chunks.
- Document aggregation: sum of the top 2 BM25 chunk scores, then top 100 document candidates.
- Cross-encoder: `BAAI/bge-reranker-v2-m3`; mỗi candidate document dùng tối đa 2 supporting chunks có BM25 score cao nhất.
- Cross-encoder document score: tổng của tối đa 2 query–chunk scores được chấm độc lập.
- Output: final top 5 documents.
- Data: fixed DEV gồm 1.036 queries.

### Candidate invariant

Candidate sets giống hệt nhau trước và sau reranking trên `1036 / 1036` queries. Candidate Recall@100 giữ nguyên ở `0.9573680823680824`; cross-encoder chỉ thay đổi thứ hạng bên trong fixed candidate set.

### Results

`Precision` và `Recall` là top-5 metrics. `MRR` được tính trong fixed top-100 scope.

| System | Precision | Recall | MRR |
|---|---:|---:|---:|
| BM25 reference | 0.16776061776061776 | 0.7865990990990991 | 0.6341294531279422 |
| Zero-shot CE reranked | 0.18127413127413128 | 0.8532818532818532 | 0.711994384154137 |
| Reranked − reference | +0.013513513513513514 | +0.06668275418275416 | +0.07786493102619474 |

Deeper-ranking deltas: Recall@10 `+0.03949485199485214`; Recall@20 `+0.025740025740025763`; Recall@50 `+0.013191763191763295`.

### DEV paired bootstrap

Paired bootstrap dùng seed `20260913` và 10.000 resamples.

| Metric | Observed delta | 95% percentile interval | Fraction delta > 0 |
|---|---:|---:|---:|
| Precision | +0.013513513513513514 | [0.008687258687258687; 0.018532818532818532] | 1.0 |
| Recall | +0.06668275418275416 | [0.044642857142857144; 0.08960746460746462] | 1.0 |

Hai intervals nằm hoàn toàn trên 0 và fraction positive bằng 1.0, cung cấp bootstrap stability evidence cho improvement quan sát được trên fixed DEV. Đây không phải automatic claim về universal statistical significance.

### Decision

DEV result chọn configuration zero-shot cross-encoder này để kiểm tra đúng một lần trên fixed local holdout với candidate set và downstream controls giữ nguyên.

## Fixed-holdout validation of zero-shot cross-encoder reranking

**Date / documentation source state:** 2026-09-14 / starting commit `bc585cd55e8552904981b5380c370b045a72dd3a`

### Question

Does the DEV-selected zero-shot cross-encoder reranking configuration generalize on the fixed local holdout without changing retrieval coverage?

### Frozen configuration

- Fixed local holdout: 1.023 queries từ `legalir_split_v1`; source SHA-256 `c39cde9e74977e350f1456e7d487aafe67d2bcbaa4fa26fcabd557fe635635b7`.
- Corpus: 8.532 documents, 199.816 fixed character-window chunks, `chunk_size=2000`, `overlap=200`.
- BM25: `bm25s==0.3.11`, `method="lucene"`, `k1=1.5`, `b=0.75`, `top_k_chunks=2000`.
- Document aggregation: sum of the top 2 BM25 chunk scores; deterministic tie-breaking giữ nguyên.
- Reranking scope: top 100 documents; mỗi candidate document dùng tối đa 2 supporting chunks có BM25 score cao nhất.
- Cross-encoder: `BAAI/bge-reranker-v2-m3`; declared offline source revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; `config_commit_hash=null`; `revision_status="declared-offline-snapshot"`. Revision này được khai báo theo offline snapshot, không được cryptographically verified hoặc metadata-verified.
- Runtime model configuration: `max_sequence_length=8192`, `dtype=float16`, `batch_size=128`, `device="cuda"`.
- Cross-encoder document score: tổng của tối đa 2 query–chunk scores được chấm độc lập.
- Output: final top 5 documents.

### Attribution check

Candidate sets giống hệt nhau trên 1.023/1.023 queries. Candidate Recall@100 có mean `0.9565004887585533`, zero-recall rate `0.033235581622678395` và full-recall rate `0.946236559139785`; Recall@100 delta sau reranking bằng đúng `0`.

Vì retrieval coverage và candidate set được giữ nguyên, các thay đổi metric quan sát được trong comparison này được quy cho việc cross-encoder thay đổi thứ hạng bên trong fixed top-100 candidate set, không phải tìm thêm document.

### Results

`Precision` và `Recall` là bundled-scorer-compatible top-5 metrics. `MRR` và Recall@K với K lớn hơn 5 là internal fixed-top-100 diagnostics.

| System | Precision | Recall | MRR | R@10 | R@20 | R@50 | R@100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 → sum-top-2 aggregation → top-100 | 0.1640273704789834 | 0.7796513522319974 | 0.6216648309745825 | 0.8397686542847833 | 0.9002117953730857 | 0.9382535027696318 | 0.9565004887585533 |
| + zero-shot BGE reranking | 0.17888563049853376 | 0.8456337569240794 | 0.711260732959998 | 0.8959758879113718 | 0.9270120560443141 | 0.9488432714239166 | 0.9565004887585533 |
| Reranked − reference | +0.014858260019550373 | +0.06598240469208194 | +0.08959590198541556 | +0.056207233626588526 | +0.026800260671228426 | +0.010589768654284737 | 0 |

Recall@5 bằng bundled-scorer-compatible recall: reference `0.7796513522319974`, reranked `0.8456337569240795`.

### Ranking diagnostics

First-gold rank distribution thay đổi như sau:

| System | Median | p90 | p95 | Rank 1 | Rank 2–5 | Rank 6–10 | Rank 11–20 | Rank 21–50 | Rank 51–100 | Not found |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Reference | 1 | 11 | 21.6 | 499 | 322 | 59 | 58 | 36 | 15 | 34 |
| Reranked | 1 | 6 | 11 | 605 | 281 | 48 | 29 | 20 | 6 | 34 |

Các thay đổi nổi bật là rank 1 `499 → 605`, p90 `11 → 6`, p95 `21.6 → 11`; số query không tìm thấy gold trong top-100 giữ nguyên `34 → 34`.

Candidate Recall@100 ceiling là `0.9565004887585533`. Gap từ ceiling đến top-5 recall giảm từ `0.1768491365265559` trước reranking xuống `0.1108667318344739` sau reranking, tức giảm `0.06598240469208194` và đóng khoảng 37,3% pre-reranking ranking gap. Đây là descriptive evidence cho fixed local holdout và configuration này, không phải universal reranking effect.

### DEV-to-holdout consistency

DEV reranked precision/recall dùng cho consistency check là `0.18127413127413128`/`0.8532818532818532`, với delta `+0.013513513513513514`/`+0.06668275418275416`. Holdout delta precision/recall là `+0.014858260019550373`/`+0.06598240469208194`. Direction đồng thuận và magnitude broadly similar giữa DEV và fixed local holdout, hỗ trợ generalization của configuration đã được chọn trên DEV.

Không chạy statistical test trên holdout. Fixed local holdout này không phải pristine test-set validation vì các giới hạn lịch sử đã được ghi trong evaluation contract và các entry trước.

### Runtime evidence

Model load mất `5.214470453999979` giây và candidate retrieval mất `4.721719871000005` giây. Run chấm `204584` query–chunk pairs; token length có median 521, p95 588, max 1524, với 0 truncated pairs và truncated fraction bằng 0. Model forward mất `455.1988099450002` giây; scoring end-to-end mất `535.9143444150001` giây; throughput tương ứng là `449.43878483495826` forward pairs/second và `381.7475724097706` end-to-end pairs/second. Peak GPU memory là `5840218112` bytes. Các số liệu này chỉ mô tả run; task không so sánh batch size hoặc hardware configuration nên không rút ra optimization conclusion.

### Interpretation

Trên fixed local holdout này, cross-encoder cải thiện đáng kể final document ranking và đóng khoảng 37,3% khoảng cách giữa Recall@100 ceiling với top-5 recall. Candidate coverage không đổi, nên kết quả validate reranking như một component hữu ích trong fixed pipeline. Residual errors vẫn gồm cả remaining ranking error trong candidate set và candidate-coverage failures ngoài top 100.

### Decision

Keep the zero-shot BGE reranker configuration as the current frozen LegalIR reranking reference.

The DEV-selected zero-shot cross-encoder configuration generalizes directionally on the fixed local holdout. Do not reopen reranker tuning without new evidence.

Current reference system:

```text
fixed-window corpus
→ BM25 top-2000 chunks
→ sum-top-2 BM25 document aggregation
→ top-100 documents
→ BGE-reranker-v2-m3
→ up to 2 supporting chunks/document
→ sum CE scores
→ final top-5
```

Decision này không cố định final output size vĩnh viễn; DEV final-selection calibration là experiment riêng đang tiếp diễn. Decision cũng không coi retrieval là đã giải quyết; dense-retrieval coverage là experiment riêng.

## Fixed final output-size calibration on frozen DEV cross-encoder ranking

### Question

Does a fixed output size smaller than 5 Pareto-improve precision and recall on the frozen cross-encoder ranking?

### Fixed comparison

Exact same frozen ranking được evaluate một lần với các prefix lengths từ 1 đến 5; không thay retrieval, candidate set, cross-encoder scoring hoặc document order.

| k | Precision | Recall |
|---:|---:|---:|
| 1 | 0.5878378378378378 | 0.5597651222651223 |
| 2 | 0.38175675675675674 | 0.7195141570141571 |
| 3 | 0.27734877734877733 | 0.7841859716859716 |
| 4 | 0.2203185328185328 | 0.8301158301158301 |
| 5 | 0.18127413127413128 | 0.8532818532818532 |

Không có `k < 5` nào Pareto-improve so với `k=5`: mọi fixed k nhỏ hơn đều tăng precision nhưng giảm recall. Riêng `k=4`, delta so với `k=5` là precision `+0.03904440154440153` và recall `-0.02316602316602312`. Chỉ 26/1.036 queries mất recall khi chuyển từ `k=5` xuống `k=4`, trong khi precision cải thiện trên 882 queries.

### Decision

Không thay `k=5` bằng một fixed k khác dựa trên experiment này. Giữ `k=5` làm current reference cho đến khi competition objective hoặc leaderboard weighting biện minh cho một trade-off khác. Adaptive final-k là một potential research axis riêng và chưa được test ở đây.

## LegalIR research state before Dense→CE holdout

Validated submission/reference system at this point:

```text
fixed-window corpus
→ BM25
→ sum-top-2 document aggregation
→ top-100 documents
→ BGE reranker
→ final top-5
```

Cross-encoder reranking đã được validate trên DEV và fixed local holdout. Fixed-k calibration không tìm thấy fixed output size dưới 5 nào Pareto-dominate `k=5`. Dense BGE-M3 retrieval cải thiện mạnh candidate coverage và hiện là active retrieval candidate cho comparison với frozen cross-encoder.

Dense → CE chưa có returned result và chưa được coi là validated.

### Public inference note

Một public-test inference notebook đã được execute cho current validated BM25 → CE system. Chưa ghi Codabench score, rank hoặc submission outcome vì chưa có submission result được cung cấp. Public test không thay thế methodology dựa trên DEV và fixed local holdout.

## Dense retrieval before the frozen cross-encoder

### Research question

Khi giữ nguyên corpus representation, candidate depth, cross-encoder và final top-5, việc thay BM25 candidate retrieval bằng BGE-M3 dense retrieval có cải thiện final LegalIR performance không?

Independent variable duy nhất là retriever family: BM25 so với BGE-M3.

### Fixed DEV controls

- Fixed DEV có 1.036 queries; source SHA-256 là `c39cde9e74977e350f1456e7d487aafe67d2bcbaa4fa26fcabd557fe635635b7`.
- Corpus giữ nguyên 8.532 documents và 199.816 source-preserving character-window chunks với `chunk_size=2000`, `overlap=200`.
- Cả hai retrievers lấy top 2.000 chunks, aggregate document bằng sum top-2 retriever chunk scores và giữ 100 candidate documents.
- Mỗi candidate dùng tối đa hai supporting chunks do chính retriever đó cung cấp: BM25 candidate dùng top BM25 chunks, dense candidate dùng top dense chunks.
- Frozen cross-encoder là `BAAI/bge-reranker-v2-m3`, declared revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, max sequence length 8.192, float16, batch size 128.
- CE document score là tổng của tối đa hai independent CE chunk scores; output cuối là top 5 documents.
- Dense model là `BAAI/bge-m3`, declared revision `5617a9f61b028005a4858fdac845db406aefb181`, revision status `declared-offline-snapshot`.
- Dense representation là L2-normalized CLS hidden state; similarity là dot product; không dùng query instruction.

### Candidate retrieval results

| Metric | BM25 | BGE-M3 | Dense minus BM25 |
|---|---:|---:|---:|
| Recall@10 | 0.8643018018018017 | 0.9227799227799228 | — |
| Recall@20 | 0.9073359073359073 | 0.9497265122265123 | — |
| Recall@50 | 0.938867438867439 | 0.9769144144144144 | — |
| Recall@100 | 0.9573680823680824 | 0.9819015444015444 | +0.024533462033462072 |
| Zero Recall@100 rate | 0.032818532818532815 | 0.013513513513513514 | — |
| Full Recall@100 rate | 0.946911196911197 | 0.9768339768339769 | — |

Candidate top-100 overlap có mean `42.50675675675676`, median `43`, p10 `24` và p90 `60`.

### Final frozen-cross-encoder results

| Metric | BM25→CE | Dense→CE | Dense→CE minus BM25→CE |
|---|---:|---:|---:|
| Bundled-scorer-compatible precision | 0.18127413127413128 | 0.18416988416988417 | +0.00289575289575289 |
| Bundled-scorer-compatible recall | 0.8532818532818532 | 0.8647039897039897 | +0.011422136422136409 |
| MRR within fixed top-100 scope | 0.7119943841541369 | 0.7291748808854571 | +0.01718049673132027 |
| Recall@10 | 0.9037966537966537 | 0.9273648648648649 | +0.023568211068211165 |
| Recall@20 | 0.9330759330759332 | 0.958976833976834 | +0.025900900900900803 |
| Recall@50 | 0.9520592020592021 | 0.9767535392535394 | +0.024694337194337224 |
| Recall@100 | 0.9573680823680824 | 0.9819015444015444 | +0.024533462033462072 |

First-gold rank diagnostics:

| First-gold rank | BM25→CE | Dense→CE |
|---|---:|---:|
| Rank 1 | 609 | 627 |
| Rank 2–5 | 299 | 291 |
| Rank 6–10 | 49 | 62 |
| Rank 11–20 | 24 | 25 |
| Rank 21–50 | 17 | 14 |
| Rank 51–100 | 4 | 3 |
| Not found | 34 | 14 |
| Median when found | 1 | 1 |
| p90 when found | 5 | 6 |
| p95 when found | 10 | 9 |

Ở final top-5, precision contribution và recall contribution đều có 64 queries improved, 923 unchanged và 49 worsened.

### Paired DEV bootstrap

Paired bootstrap dùng seed `20260913` và 10.000 resamples.

| Metric | Observed delta | 95% percentile interval | Fraction delta > 0 |
|---|---:|---:|---:|
| Precision | +0.0028957528957528956 | [-0.0013513513513513512, +0.0071428571428571435] | 0.91 |
| Recall | +0.011422136422136424 | [-0.006917631917631918, +0.03088803088803089] | 0.885 |

Cả hai competition metrics đều cải thiện theo observed DEV point estimates, nhưng cả hai bootstrap intervals đều chứa zero. Evidence vì vậy positive nhưng materially weaker so với kết quả cross-encoder-vs-reference trước đó và không statistically decisive.

### Coverage to final top-5

| System | Candidate Recall@100 | Final Recall@5 | Remaining gap |
|---|---:|---:|---:|
| BM25→CE | 0.9573680823680824 | 0.8532818532818532 | 0.10408622908622911 |
| Dense→CE | 0.9819015444015444 | 0.8647039897039897 | 0.11719755469755477 |

Dense cải thiện candidate coverage đáng kể, nhưng frozen reranker chỉ chuyển một phần coverage bổ sung đó thành final top-5 recall. Đây là descriptive comparison, không phải strict causal decomposition.

### Decision and current status

Dense→CE cải thiện cả official-style precision và recall trên DEV và được chọn làm candidate tiếp theo cho fixed-local-holdout validation. Tuy nhiên, improvement còn modest và các DEV bootstrap intervals đều chứa zero, nên Dense→CE chưa thay thế validated BM25→CE reference.

Current validated reference vẫn là:

```text
BM25
→ sum-top-2
→ top100
→ frozen BGE reranker
→ top5
```

Dense→CE status tại thời điểm này: **DEV-selected candidate awaiting fixed-local-holdout validation**. Trạng thái lịch sử này đã được supersede bởi aggregate fixed-local-holdout evidence ở entry kế tiếp.

## Fixed-local-holdout validation of Dense→CE

**Date / status:** 2026-09-15 / completed aggregate-only fixed-local-holdout run.

### Frozen configuration

Giữ nguyên 8.532 documents và 199.816 fixed character-window chunks
(`chunk_size=2000`, `overlap=200`), BGE-M3 normalized CLS dot-product retrieval,
top 2.000 dense chunks, sum top-2 dense chunk scores, top 100 unique documents,
tối đa 2 dense supporting chunks/document, frozen BGE reranker và final top-5.
Không dùng title enrichment, article-aware representation, BM25 supporting chunks,
adaptive k hay reranker mới.

### DEV evidence used for selection

| Metric | Dense→CE | Dense→CE minus BM25→CE |
|---|---:|---:|
| Precision | 0.18416988416988417 | +0.00289575289575289 |
| Recall | 0.8647039897039897 | +0.011422136422136409 |

### Fixed local holdout

| Metric | Validated BM25→CE | Dense→CE | Dense→CE minus BM25→CE |
|---|---:|---:|---:|
| Precision | 0.17888563049853376 | 0.18338220918866083 | +0.004496578690127068 |
| Recall | 0.8456337569240794 | 0.8659986966438579 | +0.020364939719778485 |
| MRR | 0.711260732959998 | 0.7299178380421532 | +0.018657105082155123 |

Internal ranking deltas của Dense→CE so với BM25→CE:

| Metric | Delta |
|---|---:|
| Recall@10 | +0.027696318018898713 |
| Recall@20 | +0.023053111762789236 |
| Recall@50 | +0.022971652003910048 |
| Recall@100 | +0.019224503095470857 |

Dense candidate Recall@100 là `0.9757249918540242`, so với BM25 candidate
Recall@100 `0.9565004887585533`. Số query không tìm thấy first gold trong
top-100 giảm từ `34` với BM25→CE xuống `17` với Dense→CE. Chỉ aggregate metrics
được dùng; fixed local holdout vẫn chịu các giới hạn đã ghi trong evaluation
contract và không được dùng để mở lại method selection.

### Decision

Dense→CE is now the current validated LegalIR reference:

```text
fixed character windows
→ BGE-M3 normalized CLS dense retrieval
→ top-2000 chunks
→ sum-top-2 dense document aggregation
→ top-100 documents with up to 2 dense supporting chunks
→ frozen BGE reranker
→ final top-5
```

Notebook public inference tương ứng có trạng thái **Code present, not executed**.
Không có public prediction hoặc Codabench result mới trong task đồng bộ này.

