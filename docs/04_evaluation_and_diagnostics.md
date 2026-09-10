# 04 — Evaluation và diagnostics

Tài liệu này là hợp đồng canonical về evaluation cho research docs. Thứ tự thẩm quyền là `scoring/` → competition data/schema → research contract → implementation trong `src/`.

## Official competition metrics

Official metric là hành vi được mã hóa trong organizer artifact dưới `scoring/`. Không thay thế bằng một library hoặc helper cùng tên nếu chưa chứng minh tương đương.

### LegalIR: submission và scorer contract

Prediction JSON là object keyed theo sample/query ID. Mỗi value phải có trường `answer`, và `answer` phải là list document ID. Scorer kiểm tra số sample prediction bằng số sample reference; các phép lookup tiếp theo đòi hỏi key prediction/reference tương ứng, nên submission hợp lệ phải giữ đúng tập sample ID.

Với gold list `G_q` và predicted list `P_q`:

```text
valid(q) = 1 ≤ len(P_q) ≤ 5

R_q = |set(G_q) ∩ set(P_q)| / len(G_q), nếu valid(q); ngược lại 0
P_q_score = |set(G_q) ∩ set(P_q)| / len(P_q), nếu valid(q); ngược lại 0

recall    = mean_q(R_q)
precision = mean_q(P_q_score)
```

Scorer ghi đúng hai key `recall` và `precision` vào `scores.json`. Đây là macro average: mỗi sample có trọng số bằng nhau.

Các behavior phải được tái tạo đúng:

- list rỗng hoặc list dài hơn 5 cho sample score recall = precision = 0;
- overlap dùng set, nên thứ tự predicted document ID không ảnh hưởng trực tiếp đến score;
- precision chia cho độ dài list gốc, không chia cho số unique prediction;
- duplicate prediction không tăng intersection, có thể giảm precision, chiếm slot và gián tiếp làm mất recall;
- scorer không tự truncate về năm và không tự deduplicate.
- một gold list rỗng sẽ gây chia cho zero khi prediction hợp lệ; data audit phải xác nhận reference không có trường hợp này thay vì tự đổi scorer.

Trong research docs, gọi `recall` này là **official recall under a maximum-5 output constraint**. `Recall@5` chỉ dùng cho local ranking diagnostic khi đã định nghĩa rõ top-5 unique documents. Repository không có authoritative artifact xác nhận metric priority hoặc tie-break.

### LegalQA: submission và scorer contract

Prediction JSON là object keyed theo sample ID; mỗi value phải có trường `answer`. Tập key cần khớp reference để các lookup trong scorer thành công. Với mỗi sample, scorer chuyển reference và prediction thành chuỗi bằng `str(...)`, sau đó tính:

- `rouge`: F-measure của `rougeL` (longest common subsequence — dãy con chung dài nhất), rồi macro-average;
- `meteor`: NLTK `meteor_score` với một reference, rồi macro-average.

Hai key output chính thức là `rouge` và `meteor`. Không suy ra primary/secondary metric từ thứ tự code hoặc tên metric.

#### Material tokenizer behavior

Bundled ROUGE scorer dùng `RougeScorer(['rougeL'], use_stemmer=False)` và default tokenizer:

1. lowercase;
2. thay mọi ký tự không thuộc ASCII `[a-z0-9]` bằng space;
3. split theo whitespace;
4. bỏ token rỗng/không khớp `[a-z0-9]+`;
5. không stemming.

Vì regex chỉ chấp nhận ASCII, dấu tiếng Việt và chữ `đ/Đ` không được bảo toàn như Vietnamese word tokens; ký tự có dấu trở thành boundary hoặc bị loại. Đây là behavior quan trọng và có thể gây kết quả khác thư viện ROUGE-L hỗ trợ Unicode. **Không sửa tokenizer trong artifact; local evaluation phải gọi hoặc faithfully reuse đúng bundled implementation.**

METEOR path không dùng tokenizer tiếng Việt: scorer gọi `.split()` trên chuỗi reference/prediction rồi truyền token vào NLTK `meteor_score`. NLTK routine mặc định lowercase khi align và có các bước exact/stem/WordNet theo dependency runtime. `scoring/` gọi download `wordnet` và `omw-1.4`, nhưng không pin NLTK version trong chính thư mục artifact; version/runtime đó là một reproducibility item còn phải fingerprint.

Extra citations, provenance hoặc giải thích nối vào submitted `answer` trở thành text được chấm và có thể thay cả ROUGE/METEOR. Submission adapter chỉ được emit `answer` theo format scorer; thông tin nội bộ phải lưu ngoài answer.

## Local research diagnostics

Diagnostics sau dùng để tìm bottleneck, không phải official scorer outputs.

### Data & corpus diagnostics

Các diagnostics này là local research diagnostics theo [00 — Data contract và preprocessing](00_data_contract_and_preprocessing.md), không phải organizer metrics và không được ghi vào official score.

**Raw data**

- schema/type/nullability theo từng file/split;
- missing/duplicate sample ID và `document_id`;
- empty/null question, answer và source text;
- split/document counts, immutable manifests và input fingerprints;
- exact/near-duplicate question analysis; duplicated answer/reference entries;
- document/passage overlap chỉ được diễn giải là leakage sau khi xét split semantics và legal-text repetition.

**Parsing**

- parse success/failure rate và failure reasons; số record bị fallback hoặc skipped;
- distribution detected part/chapter/section/article/clause/point;
- malformed numbering, impossible hierarchy transitions và parent leakage;
- overlapping, duplicate và uncovered source spans;
- source coverage ratio và stratified manual quality-control sample.

**Chunking / retrieval-unit construction**

- chunks per document và document coverage;
- token-length distribution `min/mean/median/p90/p95/p99/max` theo từng retriever/reranker/generator tokenizer liên quan;
- source-text coverage, overlap/gap distribution và accidental duplicate-chunk rate;
- truncation rate, gồm delta do context enrichment;
- số parent structural units bị một chunk cắt qua hoặc chứa đồng thời;
- intentional overlap/multi-granularity phải có flag để không bị nhầm với duplicate.

**Provenance và integrity**

- valid `chunk_id → document_id → source document` mapping rate và orphan rate;
- missing/unreliable source-span rate; exact `source_text == canonical_source[start:end]` khi offset được khai báo;
- deterministic regeneration trên identical input/config;
- input, preprocessing config, corpus/manifest và index fingerprint consistency;
- `index item count ↔ chunk manifest count ↔ chunk IDs ↔ corpus fingerprint`.

**Retrieval representation**

- `source_text` versus `retrieval_text` expansion ratio;
- title/hierarchy enrichment coverage và missing-metadata behavior;
- truncation mới phát sinh do enrichment theo từng tokenizer;
- kiểm tra derived prefix không overwrite hoặc bị trình bày như original legal text.

Corpus không được gọi `Validated` nếu có silent document loss, silent parse-error skipping, orphan chunk, unexplained duplicate, không tái tạo được mapping hoặc index không khớp manifest. Parser/chunker/validator code hiện có chỉ là `Code present` cho đến khi validation artifacts chứng minh các checks tương ứng.

### Candidate document recall

Với gold set `G_q` và top-K candidate documents đã deduplicate `C_q^K`:

```text
candidate Recall@K(q) = |G_q ∩ C_q^K| / |G_q|
```

Báo macro Recall@10/20/50/100/200, **zero-recall query rate** (`Recall@K=0`) và **full-recall query rate** (`Recall@K=1`). K là document depth sau candidate construction; nếu báo chunk depth phải đặt tên riêng.

### Complementarity

Với hai retriever A/B, báo ở cùng depth và cùng mapping:

- candidate overlap (Jaccard/overlap@K, định nghĩa cụ thể);
- unique recovered gold của A và của B;
- recall của union đã deduplicate;
- incremental latency, memory và index size.

Retriever mới chỉ đáng giữ nếu tăng coverage/complementary errors đủ bù chi phí.

### Ranking diagnostics

- Local `Recall@K` cho ranked unique document list.
- Mean Reciprocal Rank (MRR — trung bình nghịch đảo hạng của gold đầu tiên).
- normalized Discounted Cumulative Gain (nDCG — gain giảm theo hạng), nếu relevance format phù hợp.
- Candidate-ceiling gap: candidate recall trừ recall của final subset trên cùng query.

MRR/nDCG đánh giá order nội bộ; order không đi vào công thức official scorer sau khi final subset đã cố định.

### Chunk-to-document diagnostics

Báo riêng: gold-hit chunk rate; số chunk/document; số supporting chunk của mỗi candidate; document rank trước/sau aggregation; duplicate-document rate; gold document có chunk trong pool nhưng rơi khỏi final subset; distribution document coverage theo chunk depth. Luôn ghi aggregation rule và reranking diễn ra trước hay sau aggregation.

## Gold-distribution ceiling do giới hạn tối đa năm

Trước benchmark, tính `|G_q|` distribution: min, mean, median, p90, p95, max và tỷ lệ query có 1, 2, 3, 4, 5, >5 gold document. Do scorer dùng set ở tử số nhưng list length ở mẫu số, ceiling tổng quát là:

```text
maximum attainable official recall(q) = min(5, |set(G_q)|) / len(G_q)
```

Nếu gold list đã được xác nhận không có duplicate, công thức rút gọn thành:

```text
maximum attainable official recall(q) = min(5, |G_q|) / |G_q|
```

Đây là diagnostic consequence của maximum-5 constraint, không phải một metric khác. Báo macro ceiling và số query có ceiling < 1. Chưa có phân tích này thì không tuyên bố protocol verification hoàn tất. Label exhaustiveness cần audit riêng; một unlabelled document không tự động là negative.

## LegalQA internal diagnostics

Tách khỏi official `rouge`/`meteor`:

- evidence coverage và selected-evidence precision/recall, chỉ khi gold mapping đáng tin;
- claim-support/factuality rate;
- citation validity và provenance completeness trong internal record;
- unsupported/abstention rate;
- answer length và error split retrieval miss / evidence-selection / generation-grounding / formatting.

Oracle metrics chỉ hợp lệ nếu gold-evidence mapping được kiểm tra. Citation quality nội bộ không được đánh đồng với official score và citation không tự động được append vào submitted answer.

## Chẩn đoán bottleneck

```text
candidate recall cao + final official recall thấp → aggregation/reranking/subset selection
candidate recall thấp + final gần candidate ceiling → retrieval/representation/query coverage
oracle QA cao + retrieved-evidence QA thấp → retrieval/evidence selection
oracle QA thấp → generator/reasoning/answer realization hoặc gold mapping
```

“Cao/thấp” phải là threshold working hypothesis được đăng ký trước, không phải kết luận sau khi nhìn test score.

## Error taxonomy

| ID | Failure category | Câu hỏi chẩn đoán |
|---|---|---|
| F01 | Exact citation / identifier | Số hiệu, Điều/Khoản có bị tokenizer/model làm mờ? |
| F02 | Legal terminology | Thuật ngữ hiếm có được lexical branch giữ? |
| F03 | Lay-language paraphrase | Dense branch có bridge cách nói đời thường? |
| F04 | Synonym / vocabulary mismatch | Rewrite, SPLADE, dense hay PRF recover gold? |
| F05 | Multiple similar laws | Reranker phân biệt điều kiện pháp lý nhỏ? |
| F06 | Temporal/version ambiguity | Có chọn sai phiên bản/hiệu lực; metadata đủ không? |
| F07 | Title-dependent relevance | Chunk thiếu title/parent context? |
| F08 | Chunk-to-document aggregation | Gold chunk có nhưng document rank thấp? |
| F09 | Multi-document query | Maximum-5 ceiling ảnh hưởng coverage thế nào? |
| F10 | Retrieval miss | Gold không vào candidate pool ở depth đo? |
| F11 | Reranker/final-selection loss | Gold vào pool nhưng rơi khỏi submitted subset? |
| F12 | False-negative suspicion | Candidate có vẻ relevant nhưng không được label? |

## Experimental controls

- Một major axis mỗi experiment; component khác fixed.
- Cùng candidate pool khi so reranker; cùng downstream stack khi so retriever.
- Validation độc lập với public leaderboard; lưu split fingerprint.
- Báo confidence interval/paired bootstrap khi sample cho phép.
- Ghi failed/null runs, package/model revisions, scorer hash và mọi deviation.
- Không gọi `Code present` là `Validated`, hoặc gọi một run là `Benchmarked` nếu thiếu artifact tái lập.
