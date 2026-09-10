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

Trạng thái được dùng thống nhất: `Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate`, `Speculative`. Parser/chunker/validator hiện có trong `src/` chỉ là `Code present`; chưa có artifact trong repository chứng minh boundary hoặc corpus hiện tại là `Validated` hay `Benchmarked`.

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

Quan sát read-only ngày 2026-09-10 trên máy hiện tại, không phải artifact được Git quản lý:

- LegalIR và LegalQA mỗi task có local train JSON 7.000 sample và public-official JSON 1.000 sample; mỗi file là object keyed theo sample ID với hai field `question`, `answer`.
- LegalIR train dùng list document ID ở `answer`; LegalQA train dùng string; public-official của cả hai để `answer: null`.
- Exact-duplicate question groups tồn tại trong mỗi local train file, và có exact question overlap giữa hai tasks; ý nghĩa leakage/paired-task của chúng chưa được kết luận.
- Trong local LegalIR train, gold-list length quan sát được từ 1 đến 5, không có list rỗng hoặc dài hơn 5. Đây không phải claim cho dev/private/unavailable splits.
- Hai local `selected-contexts.zip` có cùng fingerprint tại thời điểm kiểm tra và chứa 8.532 JSON document. Field quan sát được là `id`, `link`, `passage`; `name` có ở một phần document.
- Snapshot có 20 record với `passage` rỗng. Đây là lý do phải báo lỗi/ngoại lệ minh bạch, không phải quyền tự động drop record.
- Raw `passage` character length rất lệch (median 23.108, p95 135.624, max 5.983.358 ký tự); đây chỉ là character diagnostic, không thay token-length measurement theo model. Có exact-duplicate non-empty passages trong snapshot, nhưng text lặp không tự động là leakage.

Các con số trên chưa thay thế D00: cần manifest, script/audit artifact tái lập được và fingerprint được lưu ngoài raw data. Private split, các bản dữ liệu khác, semantics của `link`, chất lượng `name`, document version/effective date và gold-evidence mapping vẫn chưa được xác minh.

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

Một corpus chỉ được gắn `Validated` khi có artifact chứng minh tối thiểu:

- `document_id` unique và `chunk_id` unique;
- canonical source text không rỗng, trừ exception được biện minh trong manifest;
- mọi chunk map tới document tồn tại; không orphan chunk;
- không accidental duplicate chunk; intentional overlap/duplicate phải được flag và giải thích;
- identical input + config tạo stable deterministic mapping;
- preprocessing config, input data fingerprint, corpus fingerprint/hash và mapping manifest được lưu;
- không silent document loss, silent parse-error skipping hoặc silent truncation;
- corpus được index khớp đúng manifest dùng lúc evaluation.

Với index artifact:

```text
index item count
↔ chunk manifest count
↔ ordered/set chunk IDs
↔ corpus fingerprint
```

Legacy FAISS/index artifact, nếu có, không mặc định thỏa contract. Mỗi corpus/index pair phải qua D06.

### Reproducibility artifacts tối thiểu

- immutable input/split manifest và fingerprints;
- versioned preprocessing config và code revision;
- canonical document manifest;
- chunk/evidence manifest với provenance;
- corpus fingerprint và index fingerprint;
- validation report gồm counts, exceptions, failures và deterministic-regeneration check;
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

## Baseline và dependencies

`C0` là canonical corpus baseline: một preprocessing/corpus configuration cố định, đơn giản, deterministic, auditable và đã qua integrity gate. `C0` không phải machine-learning model và không khẳng định chunk strategy tối ưu.

```text
RAW DATA
   ↓
DATA VALIDATION
   ↓
CANONICAL CORPUS (C0)
   ↓
CORPUS REPRESENTATION
   ↓
LEGALIR
   ↓
EVIDENCE
   ↓
LEGALQA
```

Exception: QA0 closed-book không phụ thuộc corpus retrieval; QA0 gold-evidence oracle có thể chạy khi gold-evidence mapping riêng đã được verify. Mọi LegalIR comparison nghiêm túc phải cố định một validated corpus manifest, còn corpus-representation experiment phải cố định downstream retrieval stack. Chi tiết experiment nằm tại [05 — Experiment map](05_experiment_map.md).
