# 00 — Data contract và preprocessing

## Vai trò và phạm vi

Tài liệu này định nghĩa **research contract** (hợp đồng nghiên cứu) để biến raw competition data thành một canonical corpus (kho dữ liệu chuẩn nội bộ) có thể cấp bằng chứng nhất quán cho cả LegalIR và LegalQA. Đây không phải tài liệu mô tả tuần tự code hiện tại và không khóa thiết kế vào một Python class, file format hay index cụ thể.

Thứ tự thẩm quyền:

```text
scoring/                     → immutable competition scoring truth
competition/local data       → raw task/data truth
docs/                        → research contract
src/                         → current implementation/prototype
```

`data/` bị Git ignore. Mọi schema hoặc thống kê nêu là quan sát từ snapshot local phải được ghi như vậy; không được suy ra dữ liệu đó đã được commit, không copy raw competition data vào Git, và không mở rộng quan sát local thành claim về private/unavailable splits.

Trạng thái được dùng thống nhất: `Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate`, `Speculative`. Hiện chỉ raw schema/loader/audit trong `src/data/` là `Code present`; parser, chunker, retrieval và modeling chưa được implement lại. Chưa có artifact được version-control để gọi raw snapshot hoặc canonical corpus là `Validated` hay `Benchmarked`.

## Preprocessing là một research layer

```text
Raw competition data
        ↓
Raw-data validation
        ↓
Minimal normalization
        ↓
Legal-structure parsing
        ↓
Retrieval-unit / chunk construction
        ↓
Metadata + structural context
        ↓
Provenance validation
        ↓
Canonical corpus
        ↓
        ├── LegalIR
        └── LegalQA evidence pipeline
```

Evidence bottleneck bắt đầu trước retriever. Thông tin bị xóa, làm sai, chia boundary không đúng hoặc map sang nhầm document trong preprocessing tạo upper bound cho cả LegalIR và LegalQA: retriever không thể khôi phục evidence không còn tồn tại hoặc không còn provenance đúng.

## Snapshot dữ liệu quan sát local

Quan sát read-only ngày 2026-09-12 trên máy hiện tại, không phải artifact được Git quản lý:

- LegalIR và LegalQA mỗi task có local train JSON 7.000 sample và public-official JSON 1.000 sample; mỗi file là object keyed theo sample ID với hai field `question`, `answer`.
- LegalIR train dùng list document ID ở `answer`; LegalQA train dùng string; public-official của cả hai để `answer: null`.
- Hai tập sample ID của LegalIR và LegalQA rời nhau ở cả train (0/7.000 ID chung) và public-official (0/1.000 ID chung); không được join hai task theo sample ID.
- Trong train có 21 exact-shared question text, phủ 22/7.000 LegalIR record (0,314%) và 26/7.000 LegalQA record (0,371%). Cardinality theo question text là 16 nhóm `1:1`, ba nhóm `1:2`, một nhóm `1:3` và một nhóm `2:1`; vì vậy exact text overlap không tạo một mapping sample one-to-one tổng quát. Public-official có đúng một exact-shared question text (`1:1`), phủ 1/1.000 record (0,1%) của mỗi task.
- Exact-duplicate question groups tồn tại trong train: LegalIR có 13 nhóm/26 record và LegalQA có 14 nhóm/29 record. Ý nghĩa leakage hoặc paired-task của các nhóm này chưa được kết luận chỉ từ text equality.
- Trong local LegalIR train, gold-list length quan sát được từ 1 đến 5, không có list rỗng hoặc dài hơn 5. Đây không phải claim cho dev/private/unavailable splits.
- Mỗi task hiện có một thư mục local `selected-contexts/` chứa 8.532 JSON document. Fingerprint toàn thư mục của LegalIR và LegalQA byte-identical tại thời điểm kiểm tra (`f1352eecb09ddb6eda530324a3d84198b8cc480f59f05edf284b2338a4c498c7`). Field quan sát được là `id`, `link`, `passage`; `name` có ở một phần document. Toàn bộ 3.105 unique gold document ID trong LegalIR train resolve được về corpus LegalIR; riêng 22 LegalIR record có exact-shared question với LegalQA chứa 24 gold assignments/19 unique document ID và tất cả đều resolve được.
- Snapshot có 20 record với `passage` rỗng. Đây là lý do phải báo lỗi/ngoại lệ minh bạch, không phải quyền tự động drop record.
- Raw `passage` character length rất lệch (median 23.108, p95 135.624, max 5.983.358 ký tự); đây chỉ là character diagnostic, không thay token-length measurement theo model. Có exact-duplicate non-empty passages trong snapshot, nhưng text lặp không tự động là leakage.

Các con số trên chưa thay thế D00: cần manifest, script/audit artifact tái lập được và fingerprint được lưu ngoài raw data. Private split, các bản dữ liệu khác, semantics của `link`, chất lượng `name`, document version/effective date và gold-document/passage/span mapping vẫn chưa được xác minh.

## Raw-data implementation hiện tại (`Code present`)

Layout local quan sát được và được `audit_all` hỗ trợ là:

```text
data_root/
├── LegalIR/
│   ├── train.json
│   ├── public-official.json
│   └── selected-contexts/*.json
└── LegalQA/
    ├── train.json
    ├── public-official.json
    └── selected-contexts/*.json
```

Caller truyền root; code không hard-code đường dẫn local hoặc Kaggle:

```python
from src.data import audit_all, save_report

report = audit_all(data_root="data", split_filename="train.json")
save_report(report, "data_audit.json")
```

`src/data/schemas.py` giữ representation raw và phân biệt field missing, JSON `null`, chuỗi rỗng và list rỗng. `src/data/loaders.py` đọc JSON file hoặc directory theo thứ tự tên deterministic; competition download cần được giải nén trước khi load. Loader không normalize, parse, chunk hoặc silently drop record. `src/data/audit.py` tạo JSON-serializable report schema version 2, fingerprint dataset/corpus của từng task, so sánh hai corpus snapshot thay vì mặc định chúng giống nhau, và chỉ reuse corpus audit khi directory fingerprints khớp chính xác.

Unit tests và full-snapshot smoke test hiện pass, nhưng đây là validation của code path trên snapshot local, không phải artifact đủ để promotion toàn bộ data/corpus layer thành `Validated`.

## Question/query representation contract

Pipeline khái niệm của mỗi task sample là:

```text
raw_question
      ↓
canonical_question
      ├── retrieval_query
      └── generator_question
```

| Representation | Contract |
|---|---|
| `raw_question` | Text câu hỏi do organizer cung cấp. Bất biến; không sửa hoặc overwrite in-place. |
| `canonical_question` | Biểu diễn source-preserving sau **chỉ** minimal normalization đã validate, ví dụ Unicode hoặc whitespace policy có version. Phải giữ wording và legal meaning; không silently rewrite ở lớp này. |
| `retrieval_query` | Biểu diễn dẫn xuất chỉ dùng cho retrieval. Có thể áp dụng tokenizer-specific preprocessing, citation normalization, legal query rewrite, multi-query expansion hoặc pseudo-relevance feedback (PRF — phản hồi liên quan giả) đã khai báo. Mỗi variant phải trỏ về `canonical_question`, có variant ID, transform/config/version và không thay thế câu hỏi gốc. |
| `generator_question` | Biểu diễn đưa vào QA generator. Mặc định bằng hoặc source-preserving từ `canonical_question`; không tự động dùng retrieval rewrite như thể đó là câu hỏi gốc. Generator-side rewriting, nếu nghiên cứu, là một QA experiment explicit với provenance riêng. |

Hard invariants:

```text
raw_question is never overwritten
canonical_question preserves semantic intent
retrieval_query is derived and versioned
generator_question is independently controlled
```

Diagnostics tối thiểu gồm null/empty question; diff Unicode/whitespace từ raw sang canonical; character/token length theo tokenizer liên quan; canonical-versus-retrieval diff; rewrite drift; bảo toàn số hiệu văn bản, Điều/Khoản/Điểm và identifiers khác; số query variants trên mỗi sample; transform/config provenance; và, khi áp dụng được, tỷ lệ rewrite token không grounded trong original query hoặc corpus. Một rewrite hữu ích theo retrieval score vẫn không được promotion nếu thêm điều kiện pháp lý hoặc làm mất identifier quan trọng.

## Cross-task LegalIR ↔ LegalQA mapping audit

D00 phải tạo mapping report dựa trên explicit keys, không suy từ việc hai task cùng dùng một corpus. Report phải tách ba câu hỏi:

1. **Observed structural relationship:** so sánh sample-ID sets; exact/canonical question text; overlap count/rate; duplicate-group cardinality; one-to-one, one-to-many và many-to-one cases; corpus snapshot fingerprint; khả năng resolve LegalIR gold document IDs.
2. **Allowed training/evaluation use:** kiểm tra rule/FAQ/forum artifact có thẩm quyền và lưu URL/version/access date. Question overlap hoặc file `train` không tự nó cấp quyền chuyển labels giữa tasks.
3. **Reliable gold-evidence mapping:** xác minh label nói tới document, passage hay exact span, và kiểm tra mapping cho từng matched sample thay vì suy rộng toàn dataset.

Snapshot trên chỉ chứng minh một **partial exact-question relationship** với disjoint sample IDs, hai corpus directories có cùng fingerprint và resolvable LegalIR document IDs. Với exact-matched question, LegalIR relevance label có thể tạo **gold-document mapping candidate** cho LegalQA nếu competition rules cho phép; nó không chứng minh document thực sự chứa mọi support cần cho QA answer, càng không tạo **gold evidence-span mapping**. Trạng thái use permission và QA support mapping vẫn `Planned`/unresolved cho đến khi có artifact audit.

## Ba lớp biểu diễn dữ liệu

### A. Raw data

Raw data là representation gốc do organizer cung cấp hoặc snapshot competition nguyên bản. Lớp này bất biến: không sửa in-place, không overwrite, không commit. Chỉ các field quan sát thực tế mới được document; field không có không được suy diễn từ tên file, link hay nội dung.

Trong snapshot local hiện có:

| Nhóm | Field quan sát | Ý nghĩa contract |
|---|---|---|
| Task sample | top-level sample ID, `question`, `answer` | Sample ID giữ identity; kiểu/nullability của `answer` phụ thuộc task/split. |
| Corpus document | `id`, `passage`, `link`, optional `name` | `id` là source identity; `passage` là source payload; `name` không phải field bắt buộc trong mọi record; semantics của `link` cần audit. |

### B. Canonical source representation

Đây là representation đã chuẩn hóa tối thiểu nhưng vẫn bảo toàn nguồn. Nguyên tắc:

```text
normalization should remove representation noise,
not legal meaning.
```

Normalization có thể chấp nhận sau khi kiểm chứng an toàn: Unicode consistency, line-ending normalization, controlled whitespace normalization, và loại formatting artifact bị lặp một cách khách quan. Mỗi transform phải có config/version và có thể đối chiếu trước–sau.

Các transform nguy hiểm, không được mặc định áp dụng: xóa punctuation hàng loạt; strip legal numbering; xóa `Điều`, `Khoản`, `Điểm`; lowercase cưỡng bức cho mọi downstream task; bỏ dấu tiếng Việt; rewrite wording pháp lý; hoặc làm mất document boundaries. Một transform hữu ích cho tokenizer/retriever vẫn phải tồn tại ở derived representation, không overwrite source-preserving text.

### C. Retrieval representation

Retrieval representation tối ưu cho matching và có thể thêm context:

```text
document title
part / chapter / section
article / clause / point
original passage
```

Enrichment phải phân biệt được với text có nguồn gốc từ document:

```text
source_text    = evidence bảo toàn từ canonical source
retrieval_text = text dùng để index/search, có thể thêm hierarchy/title
```

`source_text` và `retrieval_text` có thể khác hợp lệ, nhưng không được overwrite lẫn nhau. LegalQA đặc biệt cần biết phần nào là source evidence, phần nào là metadata/derived prefix.

## Canonical document contract

Contract mô tả khả năng biểu diễn, không áp đặt class hoặc serialization.

| Conceptual field | Loại | Invariant / semantics |
|---|---|---|
| `document_id` | Required invariant | Không rỗng, unique trong corpus manifest, map reproducibly về một raw source record. |
| source text | Required invariant | Bản source-preserving sau minimal normalization; không rỗng trừ ngoại lệ được ghi rõ. |
| available title/name | Optional source field | Chỉ có khi data cung cấp; thiếu phải là missing, không được invent. |
| available metadata | Optional source field | Giữ value và origin; không suy diễn cơ quan, hiệu lực hay loại văn bản nếu chưa có rule được validate. |
| source fingerprint/version | Required derived field | Fingerprint input/raw record hoặc source version đủ để phát hiện drift; không thay source identity. |

Unknown/unavailable field phải được biểu diễn là unknown/missing, không điền bằng phỏng đoán. Derived metadata phải có derivation rule và version riêng.

## Canonical retrieval/evidence-unit contract

| Conceptual field | Loại | Invariant / semantics |
|---|---|---|
| `chunk_id` | Required invariant | Unique; deterministic hoặc map tái lập được qua manifest. |
| `document_id` | Required invariant | Trỏ tới document tồn tại trong cùng corpus manifest. |
| `source_text` | Required invariant | Evidence slice/source-preserving text; không chứa derived prefix giả làm source. |
| `retrieval_text` | Required derived field | Input cho retrieval; có thể bằng `source_text` hoặc được enrich theo config. |
| structural path | Optional/derived | `part`, `chapter`, `section`, `article`, `clause`, `point` khi parser xác định đáng tin; không bắt buộc mọi level. |
| source span / offsets | Optional nhưng ưu tiên | Chỉ emit khi offset map về canonical source đáng tin; coordinate system phải được ghi rõ. |
| parent metadata | Optional/derived | Metadata có source/derivation rõ; không được invent để lấp missing values. |

Một document pháp luật có thể có một phần hoặc không có hierarchy dưới đây; contract không giả định mọi level luôn hiện diện:

```text
document
  └── part
       └── chapter
            └── section
                 └── article
                      └── clause
                           └── point
```

## Provenance là hard invariant

**Provenance** là khả năng truy ngược một derived chunk/evidence unit về source document và source location.

Tối thiểu:

```text
chunk → document_id → source document
```

Khi parser cung cấp đáng tin:

```text
chunk → structural unit → source span
```

Provenance là bắt buộc cho chunk→document aggregation trong LegalIR, deduplication, retrieval-error debugging, oracle/evidence analysis, LegalQA evidence tracing, phát hiện text corruption và tái tạo preprocessing experiments. `chunk_id` phải deterministic từ stable inputs/config, hoặc có mapping manifest đủ để tái lập chính xác.

## Legal-structure parsing là research problem

Regex/parser code tồn tại không chứng minh structural boundary đúng. Parsing correctness phải được đo trên actual source variants và curated/manual cases. Diagnostics tối thiểu:

- tỷ lệ document parse thành công/thất bại, kèm lý do; không silent skip;
- distribution số article/clause/point và các level khác trên mỗi document;
- numbering malformed/suspicious và impossible hierarchy transitions;
- overlapping, uncovered hoặc duplicate source spans;
- hierarchy leakage: unit nhận nhầm parent hoặc vượt qua boundary không hợp lệ;
- stratified manual inspection theo document length, fingerprint/structure type, parse outcome và edge cases.

Không có artifact đạt các kiểm tra này thì parser vẫn là `Code present`, không phải `Validated`.

## Retrieval-unit construction là research axis

Không chấp nhận giả định “fixed-size chunking chỉ là preprocessing nên không cần evaluation”. Chunking quyết định evidence nào tồn tại trong index và context generator. Candidate gồm:

- document-level, article-level, clause-level và point-level khi meaningful;
- hierarchical hoặc structure-aware bounded chunks;
- fixed-token chunks và sliding-window chunks;
- hybrid/multi-granularity indexing;
- title/parent hierarchy enrichment.

Baseline đầu tiên phải đơn giản, deterministic và auditable; không kết luận trước strategy nào tốt nhất. Alternative chỉ được gọi `Benchmarked` khi chạy downstream reproducible và có corpus diagnostics.

### Chunk boundary khác context enrichment

Hai independent axes:

```text
A. Text nào thuộc chunk?
B. Parent/title metadata nào được prepend vào retrieval_text?
```

Ví dụ khái niệm:

```text
source_text:
"Người lao động có quyền ..."

retrieval_text:
"Luật X > Chương II > Điều 15 > Khoản 2
 Người lao động có quyền ..."
```

Thay boundary và enrichment trong cùng run làm mất causal attribution. Experiments thường chỉ thay một axis, giữ downstream stack và axis còn lại cố định.

## Tokenization và length diagnostics

Character count không đại diện đủ cho neural context limits. Với từng tokenizer/model liên quan, đo riêng token-length distribution:

```text
min, mean, median, p90, p95, p99, max, truncation rate
```

Khi cần, đo riêng dense retriever tokenizer, reranker tokenizer và generator tokenizer. Không dùng length estimate của một tokenizer như universal truth; không hard-code model context length nếu chưa có authoritative model/config artifact. Enrichment phải báo cả expansion và truncation delta.

## Corpus integrity contract

### D06a — canonical corpus integrity

D06a chạy trước khi freeze C0. Một corpus chỉ được gắn `Validated` khi có artifact chứng minh tối thiểu:

- `document_id` unique và `chunk_id` unique;
- canonical source text không rỗng, trừ exception được biện minh trong manifest;
- mọi chunk map tới document tồn tại; không orphan chunk;
- không accidental duplicate chunk; intentional overlap/duplicate phải được flag và giải thích;
- identical input + config tạo stable deterministic mapping;
- preprocessing config, input data fingerprint, corpus fingerprint/hash và mapping manifest được lưu;
- source coverage được định lượng; không silent document loss, silent parse-error skipping hoặc silent truncation.

D06a không yêu cầu index tồn tại. Gate thành công cho phép freeze:

```text
C0 = frozen canonical corpus baseline
```

### D06b — index ↔ corpus alignment

D06b chạy sau khi build index cho một retriever và trước benchmark retriever đó:

Với index artifact:

```text
index item count
↔ chunk manifest count
↔ chunk/document IDs
↔ corpus fingerprint
↔ index fingerprint
```

Gate phải phát hiện stale index, index build từ corpus khác, missing/extra ID, ordering mismatch khi backend phụ thuộc ordering, và encoder/index config không tương thích. Legacy FAISS/index artifact, nếu có, không mặc định thỏa contract. Mỗi corpus/index pair phải qua D06b; D06b là prerequisite của retriever benchmark, không phải prerequisite để tạo hoặc freeze source corpus.

### Reproducibility artifacts tối thiểu

- immutable input/split manifest và fingerprints;
- versioned preprocessing config và code revision;
- canonical document manifest;
- chunk/evidence manifest với provenance;
- corpus fingerprint; index fingerprint chỉ bắt buộc khi index đã được build;
- D06a validation report gồm counts, exceptions, failures và deterministic-regeneration check; D06b alignment report cho từng index;
- tokenizer/model revisions dùng cho length/truncation diagnostics.

## Data leakage contract

D00 và mọi training/evaluation split phải kiểm tra:

- exact duplicate questions giữa/cùng splits;
- near-duplicate questions khi phương pháp đủ tin cậy;
- duplicated answer/reference entries;
- duplicated passages/documents giữa splits nếu split semantics khiến chúng tạo shortcut;
- generated/synthetic data contamination và provenance của generator/source;
- tuning lặp theo public leaderboard labels/signal;
- accidental access/use private/test answers.

Law text lặp lại không tự động là leakage: pháp luật có thể lặp, dẫn chiếu hoặc sửa đổi cùng wording. Leakage claim phải xét task semantics, split construction, source version và khả năng tạo shortcut; dedup policy không được xóa legal evidence chỉ vì text giống nhau.

### Canonical local validation split

Local validation dùng một **immutable split manifest**, không phải một lệnh random được chạy lại cho từng experiment. Generation phải deterministic; lưu fixed seed khi có randomness, explicit sample IDs cho từng split, grouping method/config/version và fingerprint của input data lẫn manifest. Không silently regenerate hoặc thay membership sau khi bắt đầu so sánh experiments.

Preferred procedure:

1. audit exact-duplicate questions;
2. tạo duplicate groups từ canonical question identity;
3. chỉ bổ sung near-duplicate groups khi phương pháp đủ precise và đã được audit để tránh gom nhầm các câu hỏi pháp lý khác nghĩa;
4. đưa toàn bộ thành viên một group vào cùng split;
5. giữ task-specific label distribution khi thực tế cho phép, nhưng không phá group boundary;
6. lưu sample IDs, group IDs, generation config/seed, data fingerprint và split-manifest fingerprint;
7. không tái sinh split âm thầm trong experiments; mọi thay đổi là một version mới, có lý do và làm mất comparability với run cũ nếu membership đổi.

Nếu một pipeline dùng paired/cross-task supervision hoặc metrics, mọi exact-shared/canonical-shared question group liên quan phải được group xuyên LegalIR và LegalQA để không truyền cùng nội dung hoặc labels qua train/validation. Khi không có cross-task information flow, report vẫn phải lưu và kiểm tra overlap thay vì mặc định bỏ qua. Chưa khóa tỷ lệ train/validation; tỷ lệ là working configuration sẽ được chọn theo dataset size, label distribution và nhu cầu thống kê, rồi freeze trong manifest.

```text
public leaderboard != local validation set
```

Repeated public-leaderboard tuning không thay thế local held-out evaluation và phải được log như một leakage/tuning risk.

## Baseline và dependencies

`C0` là canonical corpus baseline: một preprocessing/corpus configuration cố định, đơn giản, deterministic, auditable và đã qua integrity gate. `C0` không phải machine-learning model và không khẳng định chunk strategy tối ưu.

```text
RAW TASK DATA
   ↓
question/document validation + canonical local split
   ↓
canonical question + canonical source corpus
   ↓
D06a
   ↓
C0
   ↓
retrieval_query/retrieval_text + build retriever index
   ↓
D06b
   ↓
LegalIR B0 → B1 → B2
   ↓
canonical evidence records
   ↓
LegalQA G0
   ↓
QA0 → QA1 → QA2 → QA3 → QA4
```

Exception: QA0 closed-book dùng `generator_question + G0`, không phụ thuộc LegalIR. QA0 oracle chỉ chạy theo granularity thực sự được verify: gold document, gold passage hoặc gold span; `gold-document oracle != gold-span oracle`. Mọi LegalIR comparison nghiêm túc phải cố định một D06a-validated corpus manifest và chỉ benchmark sau D06b của index tương ứng; corpus-representation experiment phải cố định downstream retrieval stack. Với mọi corpus variant: `new corpus variant → D06a → build index → D06b → benchmark`. Chi tiết experiment nằm tại [05 — Experiment map](05_experiment_map.md).
