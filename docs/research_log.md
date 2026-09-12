# Research log

Đây là chronological research log, bổ sung cho các research contract và stable design documentation trong `docs/00...07`; không thay thế hoặc lặp lại toàn bộ các tài liệu đó.

Append một entry khi có result mới, một hypothesis được hỗ trợ/bác bỏ, một design decision thay đổi, hoặc một major research axis được chọn. Không log trivial refactor, formatting, test cleanup hoặc code-style change.

Các thống kê dữ liệu dưới đây là aggregate observations từ local snapshot ngày 2026-09-12. Raw data nằm ngoài Git; commit ghi trong entry xác định code/decision context, không định danh nội dung snapshot.

## D00 — Raw data understanding / audit

**Date / commit:** 2026-09-12 / `0e49c28`–`a271c35`; re-checked at `f3aa48b`

**Question**

Raw LegalIR, LegalQA và corpus thực tế có schema, quan hệ cross-task và failure conditions nào mà data layer phải bảo toàn?

**Method**

Load read-only các file train/public-official và corpus `selected-contexts/`; audit type/nullability, sample/question overlap, corpus fields, empty passage, gold-ID resolution và passage-length distribution. Không normalize text trước khi đo.

**Key results**

- LegalIR và LegalQA đều có 7.000 train samples và 1.000 public-official samples cho mỗi task.
- LegalIR train `answer` luôn là list document IDs trong snapshot; LegalQA train `answer` luôn là string. `answer` của cả hai public-official files là `null`, nên test-like data phải cho phép label vắng/null.
- Train sample IDs của hai task rời nhau hoàn toàn: 0 ID chung; không thể join LegalIR và LegalQA trực tiếp bằng sample ID.
- Có 21 exact-shared question texts trong train: 16 nhóm one-to-one, 4 one-to-many và 1 many-to-one; exact question equality không tạo mapping one-to-one tổng quát.
- Corpus có 8.532 documents. Các field quan sát được là `id`, `passage`, `link` và optional `name` (`name` có trong 7.407 documents).
- Có 20 empty passages. Cả 3.105 unique LegalIR train gold document IDs đều resolve được vào corpus; unresolved count bằng 0.
- Raw passage character length có long tail lớn: median 23.110, p95 135.538,75 và max 5.983.358 characters.

**Interpretation**

Raw files đã đủ để xây một loader/audit layer nhỏ, nhưng cross-task identity không tồn tại ở sample-ID level và question-text equality chỉ là partial, ambiguous relationship. Empty passages và extreme length outliers phải được report minh bạch; chúng không cấp quyền silently drop, repair hoặc normalize source.

**Decision**

Giữ raw loaders source-preserving: data layer trả về nội dung nguồn, không transform text, parse legal structure hay chunk. Không xây thêm schema/framework phức tạp khi chưa có research need; `src/data` chỉ phục vụ load + read-only audit.

**Next**

Khi freeze dữ liệu cho experiment, lưu manifest/fingerprint và aggregate audit artifact; audit riêng rule/permission và evidence granularity trước mọi cross-task label transfer.

## C00 — Corpus structure analysis

**Date / commit:** 2026-09-12 / `a271c35`; re-checked at `f3aa48b`

**Question**

Các line-level legal markers có coverage và consistency đủ để chọn ngay một universal structure-aware chunking strategy không?

**Method**

Chạy line-based candidate-marker diagnostics trên nguyên văn `passage`. Các regex chỉ nhận candidate `Chương`, `Mục`, `Điều` và các marker liên quan; đây không phải legal parser.

**Key results**

- Corpus size: 8.532 documents.
- Candidate `Điều`: 7.182 documents có marker, 1.350 không có marker.
- Candidate `Chương`: 4.240 documents. Candidate `Mục`: 1.442 documents.
- Document character length: median 23.110; p95 135.538,75; max 5.983.358.
- Line count: median 1.016; p95 7.149,4; max 132.712.
- Blank lines chiếm khoảng 55,16% tổng số lines.

**Interpretation**

Line breaks và legal-structure markers là tín hiệu có ích trên phần lớn corpus, nhưng corpus rất heterogeneous. Candidate article markers không có universal coverage, còn document/line lengths có long tail lớn; coverage count một mình chưa chứng minh boundary accuracy.

**Decision**

Chưa implement article parser/chunker từ C00. Phân tích candidate article segments và các failure patterns trước khi chọn chunking strategy.

**Next**

Đo segment count/length, prefix trước candidate đầu tiên, nhóm không có candidate `Điều`, và inspect representative outliers.

## C01 — Candidate article segment analysis

**Date / commit:** 2026-09-12 / `f3aa48b`

**Question**

Nếu dùng mỗi line candidate `Điều` làm boundary, các retrieval units thu được có đủ ổn định để dùng trực tiếp trên toàn corpus không?

**Method**

Với mỗi document có candidate `Điều`, tạo diagnostic segment từ start offset của candidate hiện tại đến start offset candidate kế tiếp hoặc cuối passage. Đo distributions và thresholds trên raw character offsets; inspect shortest/longest segments, longest prefixes và documents có nhiều candidates nhất.

**Key results**

- Có 151.234 candidate article segments trong 7.182 documents.
- Segment count/document: median 14; mean 21,06; p95 60; max 838.
- Segment character length: median 866; mean 2.004,03; p95 4.820; max 981.036.
- Long tail: 28.462 segments (18,82%) dài hơn 2.000 characters; 7.201 (4,76%) dài hơn 5.000; 3.226 (2,13%) dài hơn 10.000; 1.625 (1,07%) dài hơn 20.000.
- Prefix trước candidate article đầu tiên: median 987; p95 2.559,95; max 5.869.779 characters.
- Nhóm không có candidate article gồm 1.350 documents; character length median 11.849,5, mean 23.412,01, p95 73.042,55, max 759.031. Có 739/1.350 documents dài ít nhất 10.000 characters.
- Representative failures gồm false boundaries từ standards/reference text, segment chỉ chứa heading, extremely long false segments, và marker xuất hiện rất sâu trong document. Các outlier IDs tiêu biểu: `164898`, `118099`, `1992`, `4644`, `68843`.

**Interpretation**

Candidate `Điều` là useful structural signal nhưng không đủ reliable để trực tiếp làm universal retrieval unit. Regex có thể bắt cross-reference/standards text thay vì article boundary; đồng thời 1.350 documents không có candidate và nhiều document trong nhóm này vẫn rất dài.

**Decision**

Không dùng candidate article segmentation hiện tại làm C0. Giữ signal này cho validation và structure-aware corpus variants sau khi có baseline toàn-corpus.

**Next**

Chọn một C0 deterministic, model-independent và full-coverage; sau đó dùng fixed retrieval stack để đo riêng causal effect của article/structure-aware alternatives.

## C02 — C0 corpus representation decision

**Date / commit:** 2026-09-12 / working-tree decision at `f3aa48b`

**Question**

Corpus representation nào tạo baseline đơn giản, auditable và full-coverage trước khi đánh giá lợi ích của legal structure?

**Key evidence**

- C00/C01 cho thấy candidate structure có coverage đáng kể nhưng không universal và có boundary failures nghiêm trọng.
- Document và candidate-segment lengths đều có extreme long tails; article-only units không tạo length control ổn định.
- Một baseline cần tách ảnh hưởng của corpus representation khỏi retriever/reranker để attribution về sau có ý nghĩa.

**Interpretation**

Fixed-size character windows tạo control ít giả định hơn article boundaries: deterministic, model-independent, áp dụng được cho toàn corpus và không phụ thuộc độ chính xác của legal regex. Nó không được xem là optimum.

**Decision**

Baseline C0 bắt đầu bằng:

```text
fixed-size character windows + overlap
chunk_size = 2000 characters
overlap = 200 characters
```

Đây là initial baseline configuration; parameters phải dễ thay đổi. C0 không dùng article/chapter/clause regex và không normalize source text. Exact provenance là hard invariant:

```text
chunk_text == source[char_start:char_end]
```

Structure-aware/article-aware chunking không bị loại bỏ; nó được giữ làm research axis sau khi có retrieval baseline để đo causal effect trên cùng downstream stack.

**Next**

Implement C0, sau đó xây B0 BM25 và đo candidate/document Recall@K trước khi tối ưu reranking. Chỉ sau baseline này mới so sánh alternative corpus representations bằng controlled experiments.

## C03 — C0 fixed-window implementation

**Date / commit:** 2026-09-13 / `57c49e1`

**Question**

Có thể tạo một corpus baseline hoàn toàn structure-independent, deterministic và phủ toàn bộ non-empty corpus hay không?

**Configuration**

```text
character windows
chunk_size = 2000
overlap = 200
step = 1800
```

Không normalization và không dùng article/chapter/clause boundaries.

**Results**

- 8.532 corpus documents tạo 199.816 chunks.
- Chunks/document: median 13; p95 76; max 3.324.
- Chunk length: median 2.000; p95 2.000; max 2.000 characters.
- Có 20 zero-chunk documents, đúng bằng 20 empty passages; duplicate chunk IDs bằng 0.
- Largest-document examples: `68843` → 3.324 chunks; `4644` → 1.676; `42223` → 610; `164898` → 546; `12964` → 422.

**Validation**

Đã verify các provenance invariants: `chunk["text"] == source[char_start:char_end]`; mọi non-empty document có chunks và empty document có zero chunks; chunk indexes liên tục từ 0; window step bằng 1.800; final chunk chạm source end; `document_id` map ngược về source; chunk IDs unique.

**Interpretation**

C0 cung cấp retrieval-unit baseline deterministic, model-independent, không phụ thuộc legal structure regex, phủ mọi non-empty document và giữ exact source provenance. Kết quả không chứng minh cấu hình `2000/200` là optimal.

**Decision**

Freeze cấu hình này cho experiment B0 đầu tiên. Không thay chunking trong khi đánh giá BM25. Structure-aware chunking là corpus-representation experiment riêng sau khi B0 có benchmark.

## B00 — BM25 lexical baseline on C0

**Date / commit:** 2026-09-13 / working-tree benchmark after `57c49e1`

**Question**

C0 + lexical BM25 có candidate coverage bao nhiêu trước khi thêm dense retrieval/reranking?

**Fixed corpus**

```text
C0
chunk_size = 2000
overlap = 200
```

**Retrieval configuration**

- Tokenizer: lowercase rồi lấy Unicode `\w+` tokens; giữ chữ cái tiếng Việt và digits, tách punctuation; không stemming, stopword removal, segmentation hay query expansion.
- Implementation: `bm25s==0.3.11`, sparse index, explicit `method="lucene"`.
- BM25 parameters: `k1=1.5`, `b=0.75`; không tune.
- Chunk retrieval depth: `top_k_chunks=2000`. Depth 1.000 ban đầu cho 424/7.000 query dưới 200 unique documents; depth được tăng theo pool-cardinality requirement, không theo gold recall.
- Document aggregation: max BM25 score của các retrieved chunks; tương đương giữ occurrence đầu tiên của mỗi document trong sorted chunk hits.
- Chỉ giữ top 200 unique document IDs/query; full chunk-hit pools được aggregate và discard theo batch.

This is a full-train zero-shot diagnostic benchmark, not a held-out validation score. Labels chỉ được dùng để tính diagnostics sau retrieval; run này không fit/tune BM25, chunk hay depth bằng relevance labels.

**Results**

| K | candidate Recall@K | zero-recall rate | full-recall rate |
|---:|---:|---:|---:|
| 10 | 0,841374 | 0,141000 | 0,824571 |
| 20 | 0,895088 | 0,089857 | 0,880571 |
| 50 | 0,937752 | 0,050286 | 0,925571 |
| 100 | 0,959214 | 0,031714 | 0,949571 |
| 200 | 0,973917 | 0,019571 | 0,966857 |

- MRR: 0,611799.
- Official-style top-5 precision: 0,161600; official-style top-5 recall: 0,761624.
- 7.000 queries; 222 queries có zero Recall@100; 6.647 có full Recall@100; 1.393 có gold đầu tiên xuất hiện sau rank 5 nhưng không muộn hơn retained rank 200.
- Unique documents từ 2.000-chunk pool: min 128; median 676; p95 979; 8 queries dưới 200 unique documents.
- C0 construction: 2,75 s; index build: 32,59 s; retrieval + aggregation: 21,08 s trên local machine.
- 199.816 chunks indexed; sparse score arrays chiếm 248.208.568 bytes (khoảng 236,7 MiB), chưa tính Python metadata/vocabulary overhead.

**Interpretation**

Candidate coverage tăng rõ theo depth, từ 0,8414 ở K=10 lên 0,9739 ở K=200, nhưng marginal gain giảm dần: gain lần lượt khoảng 5,37; 4,27; 2,15 và 1,47 percentage points qua các depth kế tiếp. Recall@100/200 đã gần saturation nhưng chưa bão hòa hoàn toàn: 222 query vẫn zero ở K=100 và 137 query vẫn zero ở K=200.

Gap giữa official-style top-5 recall 0,7616 và candidate Recall@100/200 lần lượt khoảng 19,76/21,23 percentage points là lớn. Evidence sơ bộ cho thấy ranking/final top-5 selection là bottleneck đáng kể khi lexical candidate pool đã chứa gold sâu hơn; đồng thời zero Recall@200 còn 1,96% cho thấy retrieval coverage vẫn là residual bottleneck ở một nhóm nhỏ. Run này chưa cô lập nguyên nhân lexical mismatch, annotation exhaustiveness hay corpus representation nên không đủ để kết luận dense/hybrid chắc chắn sẽ cải thiện.

**Decision**

Giữ B00 làm lexical reference trên C0. Trước hyperparameter optimization, tạo fixed validation split; trước khi chọn dense/hybrid hay reranker, inspect zero-recall và deep-rank samples để tách coverage failure khỏi ranking failure. Không tự động chuyển sang dense/hybrid và không thay C0 từ result này.
