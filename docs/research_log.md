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
