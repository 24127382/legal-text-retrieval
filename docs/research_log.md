# Research log

Đây là chronological research log, bổ sung cho các research contract và stable design documentation trong `docs/00...07`; không thay thế hoặc lặp lại toàn bộ các tài liệu đó.

Append một entry khi có result mới, một hypothesis được hỗ trợ/bác bỏ, một design decision thay đổi, hoặc một major research axis được chọn. Không log trivial refactor, formatting, test cleanup hoặc code-style change.

Các thống kê dữ liệu dưới đây là aggregate observations từ local snapshot ngày 2026-09-12. Raw data nằm ngoài Git; commit ghi trong entry xác định code/decision context, không định danh nội dung snapshot.

## Raw data understanding / audit

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

## Corpus structure analysis

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

Chưa implement article parser/chunker từ candidate-marker diagnostics ban đầu. Phân tích candidate article segments và các failure patterns trước khi chọn chunking strategy.

**Next**

Đo segment count/length, prefix trước candidate đầu tiên, nhóm không có candidate `Điều`, và inspect representative outliers.

## Candidate article segment analysis

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

Không dùng candidate article segmentation hiện tại làm fixed corpus representation. Giữ signal này cho validation và structure-aware corpus variants sau khi có baseline toàn-corpus.

**Next**

Chọn một fixed-window corpus representation deterministic, model-independent và full-coverage; sau đó dùng fixed retrieval stack để đo riêng causal effect của article/structure-aware alternatives.

## Corpus representation decision

**Date / commit:** 2026-09-12 / working-tree decision at `f3aa48b`

**Question**

Corpus representation nào tạo baseline đơn giản, auditable và full-coverage trước khi đánh giá lợi ích của legal structure?

**Key evidence**

- Raw corpus audit và candidate article segment analysis cho thấy candidate structure có coverage đáng kể nhưng không universal và có boundary failures nghiêm trọng.
- Document và candidate-segment lengths đều có extreme long tails; article-only units không tạo length control ổn định.
- Một baseline cần tách ảnh hưởng của corpus representation khỏi retriever/reranker để attribution về sau có ý nghĩa.

**Interpretation**

Fixed-size character windows tạo control ít giả định hơn article boundaries: deterministic, model-independent, áp dụng được cho toàn corpus và không phụ thuộc độ chính xác của legal regex. Nó không được xem là optimum.

**Decision**

Fixed-window corpus representation bắt đầu bằng:

```text
fixed-size character windows + overlap
chunk_size = 2000 characters
overlap = 200 characters
```

Đây là initial baseline configuration; parameters phải dễ thay đổi. Fixed-window representation không dùng article/chapter/clause regex và không normalize source text. Exact provenance là hard invariant:

```text
chunk_text == source[char_start:char_end]
```

Structure-aware/article-aware chunking không bị loại bỏ; nó được giữ làm research axis sau khi có retrieval baseline để đo causal effect trên cùng downstream stack.

**Next**

Implement fixed-window corpus representation, sau đó xây BM25 lexical reference và đo candidate/document Recall@K trước khi tối ưu reranking. Chỉ sau baseline này mới so sánh alternative corpus representations bằng controlled experiments.

## Fixed-window implementation

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

Fixed-window corpus representation cung cấp retrieval-unit baseline deterministic, model-independent, không phụ thuộc legal structure regex, phủ mọi non-empty document và giữ exact source provenance. Kết quả không chứng minh cấu hình `2000/200` là optimal.

**Decision**

Freeze cấu hình này cho BM25 lexical reference đầu tiên. Không thay chunking trong khi đánh giá BM25. Structure-aware chunking là corpus-representation experiment riêng sau khi lexical reference có benchmark.

## BM25 lexical baseline

**Date / commit:** 2026-09-13 / working-tree benchmark after `57c49e1`

**Question**

Fixed-window corpus representation + lexical BM25 có candidate coverage bao nhiêu trước khi thêm dense retrieval/reranking?

**Fixed corpus**

```text
fixed-window corpus representation
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
- Fixed-window corpus construction: 2,75 s; index build: 32,59 s; retrieval + aggregation: 21,08 s trên local machine.
- 199.816 chunks indexed; sparse score arrays chiếm 248.208.568 bytes (khoảng 236,7 MiB), chưa tính Python metadata/vocabulary overhead.

**Interpretation**

Candidate coverage tăng rõ theo depth, từ 0,8414 ở K=10 lên 0,9739 ở K=200, nhưng marginal gain giảm dần: gain lần lượt khoảng 5,37; 4,27; 2,15 và 1,47 percentage points qua các depth kế tiếp. Recall@100/200 đã gần saturation nhưng chưa bão hòa hoàn toàn: 222 query vẫn zero ở K=100 và 137 query vẫn zero ở K=200.

Gap giữa official-style top-5 recall 0,7616 và candidate Recall@100/200 lần lượt khoảng 19,76/21,23 percentage points là lớn. Evidence sơ bộ cho thấy ranking/final top-5 selection là bottleneck đáng kể khi lexical candidate pool đã chứa gold sâu hơn; đồng thời zero Recall@200 còn 1,96% cho thấy retrieval coverage vẫn là residual bottleneck ở một nhóm nhỏ. Run này chưa cô lập nguyên nhân lexical mismatch, annotation exhaustiveness hay corpus representation nên không đủ để kết luận dense/hybrid chắc chắn sẽ cải thiện.

**Decision**

Giữ fixed-window BM25 run làm lexical reference. Trước hyperparameter optimization, tạo fixed validation split; trước khi chọn dense/hybrid hay reranker, inspect zero-recall và deep-rank samples để tách coverage failure khỏi ranking failure. Không tự động chuyển sang dense/hybrid và không thay fixed-window corpus representation từ result này.

## Fixed LegalIR train/dev/holdout split

**Date / source state:** 2026-09-13 / working tree after `1fcc0c7`

**Question**

Có thể freeze một local held-out protocol deterministic mà không để exact-duplicate raw questions đi qua split boundaries hay không?

**Assignment rule**

- Group key là exact raw `question`; không lowercase, normalize hay fuzzy/semantic group. Nếu `question` missing hoặc không phải string, group key fallback về unique sample ID. Snapshot hiện tại có 0 trường hợp cần fallback.
- Tính SHA-256 trên UTF-8 group key, lấy 8 hex digits đầu, modulo 100: bucket 0–69 vào train, 70–84 vào dev, 85–99 vào holdout.
- Rule không dùng Python `hash()`, random seed hay retrieval scores.

**Result**

| Split | Samples | Fraction |
|---|---:|---:|
| Train | 4.941 | 0,705857 |
| Dev | 1.036 | 0,148000 |
| Holdout | 1.023 | 0,146143 |
| Full | 7.000 | 1,000000 |

- Sample-ID overlap bằng 0 cho train↔dev, train↔holdout và dev↔holdout.
- Exact raw-question overlap bằng 0 cho cả ba pair.
- Union của ba ID sets bằng đúng toàn bộ 7.000 original sample IDs; mỗi ID được assign đúng một lần.

Gold-document-count distribution dưới đây dùng trực tiếp `len(answer)`:

| Gold count | Full | Train | Dev | Holdout |
|---:|---:|---:|---:|---:|
| 1 | 6.447 | 4.555 | 949 | 943 |
| 2 | 485 | 338 | 79 | 68 |
| 3 | 53 | 35 | 7 | 11 |
| 4 | 14 | 12 | 1 | 1 |
| 5 | 1 | 1 | 0 | 0 |

Drift quan sát được nhỏ; split không được search hay điều chỉnh để match distribution.

**Manifest**

- Path: `configs/legalir_split_v1.json`.
- Raw source SHA-256: `c39cde9e74977e350f1456e7d487aafe67d2bcbaa4fa26fcabd557fe635635b7`.
- Manifest SHA-256: `0fedb23fe0dfc447f3c2b321f8b6d9092c57868fe9f667df18ba00ef13eb1ccf`.

**Decision**

Freeze `legalir_split_v1`. Train dành cho supervised/domain-adaptation experiments; dev là split duy nhất dành cho error inspection, hyperparameter tuning và method selection; fixed local holdout chỉ dành cho aggregate evaluation sau khi configuration đã freeze, không phải competition test set và không được inspect theo sample trong lúc phát triển method.

## BM25 reference on fixed split

**Date / source state:** 2026-09-13 / working-tree run after `1fcc0c7`

**Question**

Pattern của full-train zero-shot BM25 diagnostic có giữ trên fixed dev/holdout hay không, và dev failures nghiêng về candidate coverage hay document ranking?

**Fixed control**

Giữ nguyên fixed-window BM25 reference: character windows 2.000/overlap 200; `bm25s==0.3.11`, `method="lucene"`, `k1=1.5`, `b=0.75`; lowercase Unicode `\w+`; `top_k_chunks=2000`; max-chunk-score document aggregation; giữ top 200 unique documents. Index build trên toàn bộ 8.532-document competition corpus, tạo 199.816 fixed character-window chunks. Chỉ query subset thay đổi.

### DEV metrics

| K | Candidate Recall@K | Zero-recall rate | Full-recall rate |
|---:|---:|---:|---:|
| 10 | 0,836631 | 0,143822 | 0,818533 |
| 20 | 0,902751 | 0,081081 | 0,888031 |
| 50 | 0,935489 | 0,051158 | 0,922780 |
| 100 | 0,953427 | 0,036680 | 0,943050 |
| 200 | 0,974743 | 0,018340 | 0,967181 |

- MRR: 0,623351.
- Official-style top-5 precision: 0,162355; official-style top-5 recall: 0,761503.
- Zero/full recall at 100: 38/977 queries. Zero/full recall at 200: 19/1.002 queries.
- Unique documents từ 2.000-chunk pool: min 143; median 674,5; p95 984; 2 queries dưới 200 unique documents.

### HOLDOUT metrics

| K | Candidate Recall@K | Zero-recall rate | Full-recall rate |
|---:|---:|---:|---:|
| 10 | 0,838058 | 0,140762 | 0,816227 |
| 20 | 0,882372 | 0,099707 | 0,864125 |
| 50 | 0,929782 | 0,055718 | 0,914956 |
| 100 | 0,952183 | 0,036168 | 0,940371 |
| 200 | 0,970023 | 0,020528 | 0,960899 |

- MRR: 0,591739.
- Official-style top-5 precision: 0,156598; official-style top-5 recall: 0,744298.
- Zero/full recall at 100: 37/962 queries. Zero/full recall at 200: 21/983 queries.
- Unique documents từ 2.000-chunk pool: min 170; median 684; p95 978,8; 1 query dưới 200 unique documents.
- Chỉ aggregate metrics được ghi; không inspect câu hỏi hay list sample IDs của holdout.

### DEV error diagnostics

- Coverage failure (`Recall@200 == 0`): 19/1.036 queries, fraction 0,018340.
- Ranking failure (có gold trong top 200 nhưng không có gold trong top 5): 207/1.036 queries, fraction 0,199807.

First-gold rank trên 1.017 dev queries có ít nhất một gold trong top 200: median 1; p90 13; p95 29,2; max 188.

| First-gold rank bin | Queries |
|---|---:|
| 1 | 510 |
| 2–5 | 300 |
| 6–10 | 77 |
| 11–20 | 65 |
| 21–50 | 31 |
| 51–100 | 15 |
| 101–200 | 19 |
| Not found | 19 |

Fraction dev queries có **all gold documents** trong candidate prefix: top 5 = 0,742278; top 10 = 0,818533; top 20 = 0,888031; top 50 = 0,922780; top 100 = 0,943050; top 200 = 0,967181.

Các bảng sau lưu tối đa 20 dev examples/family; không gán semantic cause label.

#### Coverage-failure examples

| sample_id | question | gold_document_ids | first_gold_rank | gold_ranks within top200 | gold_count |
|---|---|---|---:|---|---:|
| `12238` | Tạm hoãn thi ielts và nhiều chứng chỉ quốc tế? | `['180968']` | N/A | `[]` | 1 |
| `128348` | Chỉ huy trưởng có được quản lý đồng thời nhiều công trình? | `['89392']` | N/A | `[]` | 1 |
| `13426` | Máu gà dùng cho việc chẩn đoán bệnh viêm phế quản truyền nhiễm cần được bảo quản ở nhiệt độ bao nhiêu? | `['131890']` | N/A | `[]` | 1 |
| `148506` | Bảo đảm thuốc, vật tư y tế và việc cán bộ y tế thôi việc, bỏ việc tại các cơ sở y tế công lập? | `['147934']` | N/A | `[]` | 1 |
| `163810` | Hàm lượng chì cho phép trong sữa bột dành cho trẻ em dưới 12 tháng tuổi là bao nhiêu? | `['97249']` | N/A | `[]` | 1 |
| `34008` | Chủ tịch Ủy ban nhân dân cấp xã có thẩm quyền xử phạt học sinh gian lận mang tài liệu vào phòng thi trong kỳ thi trung học phổ thông quốc gia không? | `['278875']` | N/A | `[]` | 1 |
| `49224` | Mức phạt tiền đối với hai hành vi điều khiển xe máy chạy quá tốc độ và chuyển làn đường không đúng nơi quy định xử lý như thế nào? | `['17545']` | N/A | `[]` | 1 |
| `55540` | Hồ sơ chứng thực hợp đồng chuyển nhượng quyền sử dụng đất bao gồm những gì? | `['259656']` | N/A | `[]` | 1 |
| `60842` | Quy định về mức phụ cấp cho nhân viên hiện nay ra sao? | `['129823']` | N/A | `[]` | 1 |
| `68908` | Chất cải tạo môi trường có cần được công bố hợp quy hay không? | `['185325']` | N/A | `[]` | 1 |
| `75400` | Có những mức đánh giá xếp loại viên chức nào? | `['74494']` | N/A | `[]` | 1 |
| `76684` | Có được phép ký nhiều lần hợp đồng lao động xác định thời hạn với cùng một người lao động không? | `['129823']` | N/A | `[]` | 1 |
| `81064` | Công ty cho thuê lại tòa nhà có được xem là hành vi vi phạm pháp luật hay không? | `['223375']` | N/A | `[]` | 1 |
| `84502` | Việc nhận diện giới khác với giới tính sinh học hoàn thiện đang có được đề xuất thế nào? | `['270765']` | N/A | `[]` | 1 |
| `85530` | Hồ sơ xin cấp giấy phép xây dựng đối với công trình và nhà ở đô thị ở tỉnh Hà Giang bao gồm những gì? | `['67691']` | N/A | `[]` | 1 |
| `85654` | Thể thức của một văn bản do cơ quan nhà nước ban hành phải đáp ứng những tiêu chí nào? | `['261464', '224257']` | N/A | `[]` | 2 |
| `86710` | Có được ký hợp đồng lao động với các vị trí như sau: phục vụ hội họp, dọn dẹp vệ sinh (lao động phổ thông) và làm một công việc của Văn phòng UBND, HĐND ( lao động đã qua đào tạo Đại học) hay không? | `['75885']` | N/A | `[]` | 1 |
| `96716` | Kinh phí thực hiện đề án tuyên truyền nhằm hoàn thành các chỉ tiêu phát triển đối tượng tham gia BHXH như thế nào? | `['25075']` | N/A | `[]` | 1 |
| `99796` | Chủ tịch Ủy ban nhân dân tỉnh có thẩm quyền ra quyết định điều động công chức trong phạm vi mình quản lý không? | `['58662']` | N/A | `[]` | 1 |

#### Ranking-failure examples

| sample_id | question | gold_document_ids | first_gold_rank | gold_ranks within top200 | gold_count |
|---|---|---|---:|---|---:|
| `100152` | Trình tự lập báo cáo tình hình tài chính nhà nước được thực hiện như thế nào? | `['42598']` | 27 | `[27]` | 1 |
| `100436` | Khi nào áp dụng quy định mới tại Nghị định 33/2023/NĐ-CP? | `['145175']` | 188 | `[188]` | 1 |
| `100522` | Nhân viên chuyên môn kỹ thuật rà phá bom mìn phải đáp ứng đầy đủ các yêu cầu gì? | `['116851', '283045']` | 7 | `[7]` | 2 |
| `100590` | Đề án tuyển sinh của các trường dự bị đại học được quy định như thế nào? | `['206812']` | 9 | `[9]` | 1 |
| `100698` | Tàng trữ hóa chất chưa được phép sử dụng ở Việt Nam thì có bị xử lý hình sự hay không? | `['245154']` | 15 | `[15]` | 1 |
| `101642` | Có hình thức đào tạo nào cho người đi làm tham gia học tập tại trường đại học không? | `['146481']` | 38 | `[38]` | 1 |
| `101762` | Các ngày nghỉ thuộc về diện nghỉ lễ, tết được quy định như thế nào? | `['129823']` | 6 | `[6]` | 1 |
| `102220` | Cha mẹ có hành vi bạo hành con trai của mình được hiểu như thế nào? | `['96450', '121603']` | 9 | `[9]` | 2 |
| `10264` | Hồ sơ xin cấp giấy phép lưu hành xe được pháp luật quy định như thế nào? | `['192790']` | 14 | `[14]` | 1 |
| `102902` | Làm và sử dụng Sổ đăng kiểm xe ô tô giả thì tổng hợp hình phạt ra sao? | `['245154']` | 109 | `[109]` | 1 |
| `103692` | Xét nâng ngạch Giảng viên chính cần chứng chỉ gì? | `['16157']` | 49 | `[49]` | 1 |
| `104238` | Uống rượu bia gây tai nạn giao thông chết người bồi thường cho người bị tai nạn như thế nào? | `['81598']` | 119 | `[119]` | 1 |
| `105976` | Hạn mức công nhận đất ở đối với trường hợp thửa đất có vườn, ao được ở tỉnh Hòa Bình được quy định ra sao? | `['235996']` | 17 | `[17]` | 1 |
| `107964` | Đăng ký kết hôn cần những giấy tờ gì mới nhất năm 2023? | `['157168']` | 9 | `[9]` | 1 |
| `108182` | Xử phạt đối với hành vi không thông báo lưu trú cho khách? | `['98892']` | 7 | `[7]` | 1 |
| `108738` | Người dân có bắt buộc phải đóng góp tiền để làm đường liên ấp không? | `['11864']` | 168 | `[168]` | 1 |
| `108936` | Bộ luật Hình sự mới nhất 2023 là Bộ luật nào? | `['245154']` | 6 | `[6]` | 1 |
| `110510` | Việc đánh giá từng tiêu chí an toàn thực phẩm đối với cơ sở kinh doanh muối được hướng dẫn ra sao? | `['92057']` | 10 | `[10]` | 1 |
| `111188` | Mức phí cho việc thực hiện thủ tục thay đổi họ là bao nhiêu? | `['102478']` | 114 | `[114]` | 1 |
| `111990` | Thời hiệu xử phạt vi phạm hành chính đối với cơ sở tiêm chủng khám sàng lọc không đầy đủ cho đối tượng được tiêm chủng là bao lâu? | `['17545']` | 155 | `[155]` | 1 |

### Interpretation

So với full-train BM25 diagnostic, dev/holdout giữ cùng pattern. Candidate Recall@100/200 lần lượt là 0,9534/0,9747 trên dev và 0,9522/0,9700 trên holdout, gần full-train 0,9592/0,9739. Official-style top-5 recall là 0,7615 trên dev và 0,7443 trên holdout, so với full-train 0,7616. Holdout thấp hơn nhẹ ở top-5/MRR nhưng không thay đổi qualitative conclusion.

Khoảng cách Recall@200 với top-5 recall vẫn lớn: khoảng 21,32 percentage points trên dev và 22,57 points trên holdout. Trên dev, 207 ranking failures lớn hơn nhiều 19 coverage failures. Đây là evidence aggregate rằng ranking/final selection là bottleneck chính của fixed-window BM25 reference trên split v1; diagnostics chưa xác định lexical mismatch, annotation error hay corpus-representation error.

### Decision

Giữ fixed-window BM25 run làm unchanged reference và freeze split v1. Pattern `high Recall@100/200` nhưng `significantly lower top-5 recall` được lặp lại, nên major axis tiếp theo là **document ranking / chunk→document aggregation**, chỉ tune/chọn method bằng dev. Holdout không được dùng để thay đổi method. Task này không implement retrieval, aggregation hay reranking alternative nào.

## Evaluation protocol clarification

**Date / source state:** 2026-09-13 / protocol clarification after fixed-split reference run

### Reason

- Holdout usage cần strict hơn để các development iterations không biến aggregate held-out estimate thành selection signal.
- Current holdout không pristine vì full-7.000-query zero-shot BM25 diagnostic và một số aggregate/failure information đã được inspect trước khi split được freeze.
- Candidate Recall@K cần explicit effective-depth semantics khi candidate pool có ít hơn K unique documents.

### Protocol decision

- [Evaluation contract](04_evaluation_and_diagnostics.md#dev-và-fixed-local-holdout) là canonical: dev là split duy nhất cho method selection, error inspection và hyperparameter tuning. Holdout chỉ được evaluate ở aggregate level sau khi configuration đã được chọn bằng dev và freeze; không inspect holdout samples/failure IDs, không sửa method từ holdout errors và không chọn giữa alternatives bằng holdout score.
- Gọi split này là **fixed local holdout**. Nó vẫn hữu ích cho relative generalization và chưa có tuning trực tiếp trên holdout IDs, nhưng không phải pristine untouched, independent hoặc final test set theo strict experimental design.
- Với requested depth K, candidate recall dùng `effective_k(q) = min(K, len(ranked_unique_documents_q))`. Query có list ngắn hơn K dùng toàn bộ available prefix; đây là limited-candidate-pool condition, không phải bug.
- Future comparisons phải report minimum/median/p95 unique candidate documents và `queries_below_depth` cho các candidate depths được evaluate.
- Existing aggregate holdout metrics ở entry trước thiết lập current reference. Future development iterations không repeatedly evaluate holdout.

Entry này không ghi experimental result mới và không thay split assignment, retrieval configuration hoặc metric implementation.

## Document aggregation comparison on fixed BM25 candidates

**Date / source state:** 2026-09-13 / fixed DEV split and unchanged BM25 retrieval controls

### Question

Does document aggregation explain part of the gap between high candidate coverage and lower top-5 performance?

### Fixed controls

- Corpus representation: fixed-window character chunks, size 2.000 và overlap 200; 199.816 chunks từ toàn bộ 8.532 documents.
- Retrieval: `bm25s==0.3.11`, `method="lucene"`, `k1=1.5`, `b=0.75`, lowercase Unicode `\w+` tokenizer và `top_k_chunks=2000`.
- Data: cùng fixed DEV split gồm 1.036 queries; source SHA-256 khớp manifest (`c39cde9e74977e350f1456e7d487aafe67d2bcbaa4fa26fcabd557fe635635b7`).
- Mỗi DEV query được retrieve đúng một lần. Cả bốn aggregation variants dùng cùng exact top-2.000 chunk-hit pool gồm `chunk_id`, `document_id`, BM25 score và chunk rank.
- Candidate universe của mỗi query là toàn bộ unique document IDs trong shared chunk-hit pool; không prefilter bằng max score. Sau aggregation mới lấy prefix tại requested document depth.
- Tie-break chung: aggregate score giảm dần, sau đó best chunk rank tăng dần, rồi canonical string `document_id` tăng dần.

### Aggregation variants

- Max chunk score.
- Mean top-2 chunk scores; document có một hit dùng score đó.
- Mean top-3 chunk scores; document có ít hơn ba hits dùng mean trên số hits hiện có.
- Sum top-2 chunk scores; document có một hit dùng score đó.

### Results

Candidate Recall@K và MRR dùng document-ranking prefix đến depth 200 như current reference; candidate-pool recall và first-gold `not found` dùng complete shared candidate universe.

| Aggregation | Recall@10 | Recall@20 | Recall@50 | Recall@100 | Recall@200 | MRR | Top-5 precision | Top-5 recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Max chunk score | 0,836631 | 0,902751 | 0,935489 | 0,953427 | 0,974743 | 0,623351 | 0,162355 | 0,761503 |
| Mean top-2 | 0,863819 | 0,909508 | 0,936454 | 0,956966 | 0,973456 | 0,631326 | 0,166216 | 0,778394 |
| Mean top-3 | 0,848858 | 0,899533 | 0,933237 | 0,956001 | 0,970721 | 0,626459 | 0,164672 | 0,770672 |
| Sum top-2 | 0,864302 | 0,907336 | 0,938867 | 0,957368 | 0,972651 | 0,634224 | 0,167761 | 0,786599 |

Delta trực tiếp so với max chunk score:

| Aggregation | Δ Recall@10 | Δ Recall@20 | Δ Recall@50 | Δ MRR | Δ top-5 precision | Δ top-5 recall |
|---|---:|---:|---:|---:|---:|---:|
| Mean top-2 | +0,027188 | +0,006757 | +0,000965 | +0,007975 | +0,003861 | +0,016892 |
| Mean top-3 | +0,012227 | -0,003218 | -0,002252 | +0,003108 | +0,002317 | +0,009170 |
| Sum top-2 | +0,027671 | +0,004585 | +0,003378 | +0,010873 | +0,005405 | +0,025097 |

Zero/full-recall diagnostics:

| Aggregation | Zero @100 | Full @100 | Zero @200 | Full @200 |
|---|---:|---:|---:|---:|
| Max chunk score | 0,036680 | 0,943050 | 0,018340 | 0,967181 |
| Mean top-2 | 0,031853 | 0,945946 | 0,019305 | 0,966216 |
| Mean top-3 | 0,033784 | 0,945946 | 0,021236 | 0,962355 |
| Sum top-2 | 0,032819 | 0,946911 | 0,020270 | 0,964286 |

Candidate-pool recall, measured over every unique document in the shared top-2.000 chunk pool, là 0,986326 cho mọi variant; zero-recall rate là 0,010618, full-recall rate là 0,982625, 1.025/1.036 queries có ít nhất một gold document và 11 queries không có gold document trong pool. Implementation check xác nhận candidate universe giống nhau cho cả bốn methods trên 1.036/1.036 queries.

Candidate-pool sufficiency: số unique documents/query có minimum 143, median 674,5 và p95 984. Không query nào dưới depth 10/20/50/100; 2 queries dưới depth 200 và được tính bằng toàn bộ available prefix theo evaluation protocol.

Per-query official-style top-5 comparison với max chunk score:

| Aggregation | Precision improved / unchanged / worsened | Recall improved / unchanged / worsened |
|---|---:|---:|
| Mean top-2 | 40 / 976 / 20 | 40 / 976 / 20 |
| Mean top-3 | 49 / 949 / 38 | 49 / 949 / 38 |
| Sum top-2 | 48 / 969 / 19 | 48 / 969 / 19 |

First-gold ranks được tính trên complete candidate universe, không coi document sau rank 200 là absent; median/p90/p95 được tính trên các query tìm thấy ít nhất một gold document:

| Aggregation | Median | p90 | p95 | Rank 1 | Rank 2–5 | Rank 6–10 | Rank 11–20 | Rank 21–50 | Rank 51–100 | Rank 101–200 | Beyond 200 | Not found |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Max chunk score | 2 | 14 | 38 | 510 | 300 | 77 | 65 | 31 | 15 | 19 | 8 | 11 |
| Mean top-2 | 1 | 11,6 | 37,4 | 514 | 316 | 85 | 44 | 24 | 20 | 13 | 9 | 11 |
| Mean top-3 | 2 | 13 | 45,8 | 510 | 314 | 76 | 49 | 31 | 21 | 13 | 11 | 11 |
| Sum top-2 | 1 | 11 | 39 | 515 | 323 | 78 | 40 | 29 | 17 | 13 | 10 | 11 |

Supporting-chunk count trên mọi query-document candidate pair có median 1, p95 10 và max 407 retrieved chunks. Đây là pool-level diagnostic; không phải feature analysis hay learned signal.

### Interpretation

Rewarding multiple strong lexical chunks có ích trên DEV. Sum top-2 tăng đồng thời official-style top-5 precision (+0,005405), top-5 recall (+0,025097), MRR (+0,010873) và Recall@10/20/50 so với max-score, trong khi retrieval và candidate-pool recall giữ nguyên. Mean top-2 cũng tăng đồng thời top-5 precision/recall và MRR nhưng nhỏ hơn sum top-2. Mean top-3 tăng top-5 scores nhưng giảm Recall@20 và Recall@50, nên evidence kém ổn định hơn qua ranking depths.

Mean aggregation không gây net loss trên top-5 aggregate metrics, nhưng có per-query regressions: 20 queries worsened với mean top-2 và 38 với mean top-3. Cùng với deeper-recall losses của mean top-3, kết quả phù hợp với rủi ro averaging làm giảm hạng document được nâng bởi một strong chunk; pool-level supporting-count diagnostic hiện tại chưa đủ để gán trực tiếp mỗi regression cho trường hợp đó.

Improvement không trải trên đa số queries: sum top-2 thay đổi top-5 outcome ở 67/1.036 queries, gồm 48 improved và 19 worsened; 969 unchanged. Vì vậy gain có hướng nhất quán trên nhóm queries bị ảnh hưởng nhưng vẫn localized.

Khoảng cách giữa fixed candidate-pool recall và top-5 recall giảm từ 0,224823 với max score xuống 0,199727 với sum top-2, tức giảm 0,025097 absolute (khoảng 11,16% của gap ban đầu) mà không thay retrieval coverage. Aggregation giải thích được một phần, không phải toàn bộ ranking gap.

### Decision

Sum top-2 có evidence DEV mạnh nhất trong comparison nhỏ này vì cải thiện đồng thời cả official-style precision và recall, đồng thời cải thiện MRR và Recall@10/20/50. Freeze sum top-2 làm document-ranking rule candidate trước khi có bất kỳ fixed local holdout evaluation nào. Task này không evaluate holdout và chưa chuyển sang dense retrieval, hybrid retrieval hay reranking.

## Official scorer validation and fixed-holdout check

**Date / source state:** 2026-09-13 / commit `0260afa342f33cd1f083b9ce4fe8504f75638129`, fixed split và frozen document aggregation decision

### Purpose

- Verify local top-5 evaluation against `eval_retrieval` trong bundled LegalIR scorer tại `scoring/LegalIR/scoring.py`.
- Quantify stability của DEV improvement dưới paired query resampling.
- Evaluate aggregation đã freeze bằng DEV đúng một lần trên fixed local holdout ở aggregate level.

### Official scorer validation

Prediction adapter giữ nguyên sample IDs và tạo đúng object `{sample_id: {"answer": [...]}}`; mỗi answer chứa top 5 unique ranked document IDs, không threshold, adaptive K hay extra field. DEV run giữ nguyên 1.036 queries, full-corpus fixed-window representation và shared top-2.000 chunk-hit pool.

| Aggregation | Bundled scorer precision | Local top-5 precision | Absolute difference | Bundled scorer recall | Local top-5 recall | Absolute difference |
|---|---:|---:|---:|---:|---:|---:|
| Max chunk score | 0,16235521235521233 | 0,16235521235521236 | 2,7755575615628914e-17 | 0,7615025740025740 | 0,7615025740025739 | 1,1102230246251565e-16 |
| Sum top-2 | 0,16776061776061776 | 0,16776061776061776 | 0 | 0,7865990990990991 | 0,7865990990990991 | 0 |

Mọi absolute difference đều nhỏ hơn `1e-12`; bundled scorer equivalence pass. Bundled scorer được load trực tiếp bằng `importlib` và gọi `eval_retrieval(prediction, truth)`; authoritative scorer không được sửa hoặc reimplement cho validation này.

### DEV paired bootstrap

Paired bootstrap resample cùng query indices cho max chunk score và sum top-2. Per-query contributions được lấy bằng direct singleton calls tới bundled scorer. Seed là `20260913`, số resamples là 10.000; rerun với cùng seed trả về đúng cùng summary.

| Metric | Observed delta | Bootstrap mean delta | 95% percentile interval | Fraction delta > 0 |
|---|---:|---:|---:|---:|
| Precision | +0,005405405405405405 | +0,005419498069498070 | [0,002316602316602317; 0,008494208494208495] | 0,9998 |
| Recall | +0,025096525096525095 | +0,025169015444015445 | [0,010939510939510939; 0,039736164736164730] | 0,9998 |

Cả hai paired bootstrap 95% percentile intervals đều hoàn toàn lớn hơn 0. Improvement của frozen sum-top-2 aggregation có bootstrap stability trên DEV; diagnostic này không được dùng để search hoặc chọn thêm aggregation variant.

### Fixed local holdout

Holdout evaluation chỉ chạy sau khi scorer equivalence pass. Hai configurations dùng cùng 1.023 queries, 8.532-document corpus, 199.816 fixed character-window chunks với size 2.000/overlap 200, `bm25s==0.3.11`, `method="lucene"`, `k1=1.5`, `b=0.75`, lowercase Unicode `\w+`, `top_k_chunks=2000`, shared candidate universe và deterministic aggregation tie-break.

**Bundled LegalIR scorer metrics**

| Aggregation | Official scorer precision | Official scorer recall |
|---|---:|---:|
| Max chunk score | 0,1565982404692082 | 0,7442978168784621 |
| Sum top-2 | 0,1640273704789834 | 0,7796513522319974 |

Official scorer deltas của sum top-2 so với max chunk score: precision `+0,007429130009775187`; recall `+0,03535353535353536`.

**Internal aggregate diagnostics**

| Aggregation | Recall@10 | Recall@20 | Recall@50 | Recall@100 | Recall@200 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| Max chunk score | 0,8380579993483219 | 0,8823721081785597 | 0,9297816878462040 | 0,9521831215379603 | 0,9700228087324861 | 0,5917688824236508 |
| Sum top-2 | 0,8397686542847833 | 0,9002117953730857 | 0,9382535027696318 | 0,9565004887585533 | 0,9692082111436950 | 0,6217792191562832 |

Internal deltas: Recall@10 `+0,001710654936461387`; Recall@20 `+0,017839687194526000`; Recall@50 `+0,008471814923427856`; Recall@100 `+0,004317367220593060`; Recall@200 `-0,000814597588791099`; MRR `+0,030010336732632426`. Recall@K với K lớn hơn 5 và MRR là internal diagnostics, không phải official scorer metrics.

Candidate-pool recall trên complete shared candidate universe là `0,9850114043662430`; zero-recall rate `0,009775171065493646`, full-recall rate `0,9794721407624634`, 1.013/1.023 queries có ít nhất một gold document trong pool. Candidate-pool sufficiency: minimum 170, median 684, p95 978,8 unique documents/query; số queries dưới depth 10/20/50/100/200 lần lượt là 0/0/0/0/1. Candidate universe giống nhau cho cả hai aggregations trên toàn bộ holdout run.

Fixed local holdout không phải pristine untouched test set. Sum top-2 đã được freeze trước evaluation này; không inspect sample-level holdout questions, IDs, failure examples hay wins/losses. Kết quả chỉ được record ở aggregate level và không được dùng để search variants trong task này.

### Decision

The DEV-selected sum-top-2 aggregation generalizes directionally on the fixed local holdout.

Có thể giữ sum top-2 làm current fixed document aggregation reference cho các experiment tiếp theo. Decision này không mở lại aggregation search và không thay retrieval, chunking, tokenizer, BM25 controls hay split.

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

## BGE-M3 dense retrieval coverage on fixed DEV split

### Question

Does multilingual dense retrieval improve candidate coverage and recover relevant documents missed by BM25?

### Fixed controls and implementation

- Corpus và representation giữ nguyên: 8.532 documents, 199.816 fixed character-window chunks, `chunk_size=2000`, `overlap=200`.
- Data giữ nguyên: fixed DEV gồm 1.036 queries.
- Retrieval depth: top 2.000 chunks.
- Document aggregation: sum of the top 2 retrieval chunk scores.
- Không dùng cross-encoder và không dùng fusion.
- Dense model: `BAAI/bge-m3`; declared revision `5617a9f61b028005a4858fdac845db406aefb181` từ offline snapshot; config commit hash unavailable.
- Embedding implementation: L2-normalized CLS hidden state từ Transformers `AutoModel`; similarity là dot product.

### Recall comparison

| K | BM25 | BGE-M3 |
|---:|---:|---:|
| 10 | 0.8643018018018017 | 0.9227799227799228 |
| 20 | 0.9073359073359073 | 0.9497265122265123 |
| 50 | 0.938867438867439 | 0.9769144144144144 |
| 100 | 0.9573680823680824 | 0.9819015444015444 |
| 200 | 0.9726512226512226 | 0.9877734877734878 |

MRR của BM25 là `0.6342514700877372`; MRR của dense retrieval là `0.7159583402955311`.

### Complementarity

Tại top 100, số gold documents theo coverage category là: found by both `1067`, BM25-only `6`, dense-only `39`, neither `20`. Có 37 queries với ít nhất một dense-only recovered gold và 6 queries với ít nhất một BM25-only recovered gold.

Union Recall@100 ceiling là `0.986003861003861`, so với dense Recall@100 `0.9819015444015444`; vì vậy union chỉ thêm khoảng `0.00410` absolute recall so với dense alone ở depth này.

Tại top 200, BM25 Recall là `0.9726512226512226`, dense Recall là `0.9877734877734878`, và union Recall là `0.9909909909909909`.

### Interpretation

Dense retrieval mạnh hơn BM25 dưới fixed representation và genuinely complementary vì recover được relevant documents mà BM25 bỏ lỡ. Tuy nhiên, dense alone đã chiếm phần lớn observed union coverage gain.

### Decision

Không chuyển thẳng sang hybrid fusion. Controlled experiment tiếp theo là `BGE-M3 dense retrieval → frozen validated cross-encoder`, được so sánh với `BM25 → frozen validated cross-encoder` trong khi giữ cố định mọi downstream variable.

## Current LegalIR research state

Validated current submission/reference system:

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

Dense→CE status: **DEV-selected candidate awaiting fixed-local-holdout validation**.
