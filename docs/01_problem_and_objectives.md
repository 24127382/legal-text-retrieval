# 01 — Bài toán và mục tiêu

## Ba research axes, một evidence bottleneck

Project có ba research axes phụ thuộc nhau:

- **Axis A — Data & Corpus Representation**: kiểm tra raw data, bảo toàn source, parse cấu trúc pháp luật, tạo retrieval/evidence units và provenance.
- **Axis B — LegalIR** (Legal Information Retrieval — truy hồi thông tin pháp luật): nhận câu hỏi pháp lý và chọn các ID văn bản liên quan.
- **Axis C — LegalQA** (Legal Question Answering — hỏi đáp pháp luật): dùng câu hỏi và evidence để tạo câu trả lời.

Cả hai task downstream cùng chịu một **evidence bottleneck**, và bottleneck này bắt đầu trước retriever. Nếu preprocessing xóa/corrupt nội dung, segment sai hoặc map chunk sang nhầm document, không retriever/reranker/generator nào có thể khôi phục evidence đúng.

```text
raw data
   ↓
corpus representation
   ↓
evidence retrieval
   ↓
candidate/evidence pool
   ├─ LegalIR: document construction → aggregation/reranking → final subset
   └─ LegalQA: evidence selection → grounded generation → verification → answer
```

Ngược lại, nếu evidence đã có nhưng LegalQA vẫn sai, lỗi có thể nằm ở chọn đoạn, suy luận, grounding (ràng buộc câu trả lời vào bằng chứng) hoặc answer realization (cách diễn đạt đầu ra). Thay retriever khi đó không nhất thiết giải đúng nguyên nhân.

## Mục tiêu nghiên cứu

### Axis A — Data & Corpus Representation

1. Bảo toàn legal meaning và document identity từ raw source.
2. Validate structural parsing bằng diagnostics và manual inspection, không suy từ việc parser code tồn tại.
3. Tạo retrieval/evidence units đơn giản, deterministic và auditable.
4. Bảo toàn provenance `chunk → document_id → source document`, và source span khi đáng tin.
5. Đo chunking/representation choices thay vì coi chúng là fixed preprocessing mặc định.
6. Freeze canonical corpus baseline `C0` trước khi so sánh major LegalIR methods.

### Axis B — LegalIR

1. Tối đa hóa candidate coverage bằng các tín hiệu truy hồi bổ sung nhau.
2. Đo candidate recall trước khi tối ưu reranking.
3. Phân biệt rõ chunk retrieval, candidate document construction, document aggregation, reranking và final subset selection.
4. Dùng tối đa năm vị trí output theo đúng scorer chính thức.
5. Chỉ thay đổi một major research axis trong mỗi thí nghiệm để giữ attribution.

### Axis C — LegalQA

1. Tiêu thụ canonical evidence records theo data contract và tái sử dụng tầng evidence retrieval đã được đo của LegalIR.
2. Dùng oracle control khi và chỉ khi có mapping gold evidence đáng tin cậy.
3. Tách retrieval error, evidence-selection error và generation/grounding error.
4. Đặt factual grounding trước tối ưu hóa hình thức theo metric.

## Hành vi chính thức đã xác định từ `scoring/`

### LegalIR

Submission và reference là các JSON object keyed theo sample/query ID. Với mỗi prediction ID, value phải chứa trường `answer`; `answer` là một list document ID. Tập ID prediction phải khớp tập ID reference để scorer có thể chấm đầy đủ.

Với query `q`, gọi list dự đoán là `P_q` và list gold là `G_q`:

```text
valid(q)       := 1 ≤ |P_q| ≤ 5
recall(q)      := |set(G_q) ∩ set(P_q)| / |G_q|       nếu valid(q), ngược lại 0
precision(q)   := |set(G_q) ∩ set(P_q)| / |P_q|       nếu valid(q), ngược lại 0
official score := macro mean của recall(q) và precision(q) trên các sample
```

Các hệ quả trực tiếp:

- output rỗng hoặc dài hơn 5 nhận recall và precision bằng 0 cho sample đó;
- overlap dùng set, nên thứ tự ID trong `answer` không trực tiếp ảnh hưởng điểm;
- duplicate ID không tạo thêm overlap nhưng vẫn chiếm chỗ và vẫn nằm trong mẫu số precision, nên có thể làm giảm precision và làm mất cơ hội đưa một document khác vào tối đa năm slot;
- cách gọi chính xác cho recall chính thức là **official recall under a maximum-5 output constraint**, không mặc định đồng nhất với local `Recall@5`;
- scorer trả cả `recall` và `precision`, nhưng repository không chứa artifact có thẩm quyền quy định metric nào là primary hoặc cơ chế tie-break.

### LegalQA

Submission là JSON object keyed theo sample ID; mỗi value phải chứa trường `answer`. Scorer ép reference và prediction qua `str(...)`, rồi trả hai giá trị macro-mean:

- `rouge`: ROUGE-L F-measure từ bundled `rouge_score`, `use_stemmer=False`;
- `meteor`: NLTK `meteor_score` trên token tạo bằng `.split()`.

Repository không cung cấp artifact có thẩm quyền để suy ra ưu tiên giữa `rouge` và `meteor`. Chi tiết tái tạo metric và tokenizer được quy định tại [04 — Evaluation và diagnostics](04_evaluation_and_diagnostics.md).

## Schema dữ liệu quan sát được

Các JSON task hiện có trong local `data/LegalIR/` và `data/LegalQA/` đều là object keyed theo sample ID:

- LegalIR train: value có `question` và `answer`, trong đó `answer` là list document ID; public-official giữ cùng hai field và để `answer: null`.
- LegalQA train: value có `question` và `answer`, trong đó `answer` là chuỗi; public-official giữ cùng hai field và để `answer: null`.

Local corpus archive quan sát được chứa document JSON với `id`, `passage`, `link` và optional `name`. Đây là quan sát read-only trên dữ liệu bị Git ignore ở máy hiện tại, không phải tuyên bố các file đó được version-control hoặc schema này đúng cho mọi split/phiên bản. Contract đầy đủ nằm tại [00 — Data contract và preprocessing](00_data_contract_and_preprocessing.md).

## Known / Unknown / Must Verify

### Known

- Official scorer contract và tên output metric đã có trong `scoring/`.
- Data & Corpus Representation là prerequisite của LegalIR và evidence-grounded LegalQA.
- LegalIR và LegalQA có thể chia sẻ tầng retrieval nhưng có submission adapter khác nhau.
- Code trong `src/` có parser/chunker và prototype dense chunk retrieval; đây là `Code present`, không phải `Validated` hay `Benchmarked`.
- B2 trong tài liệu là reference design `Planned`, không phải hệ thống đã hoàn thành.

### Unknown

- Quy mô và quan hệ chính xác của train/dev/public/private ngoài các file hiện có.
- Phân bố số gold document ngoài local train snapshot và mức đầy đủ của relevance labels.
- Mapping gold evidence cho LegalQA có tồn tại và đủ tin cậy cho oracle hay không.
- Độ dài document/chunk theo từng tokenizer, chất lượng metadata và thông tin phiên bản/hiệu lực.
- Quy tắc external model/data/API; giới hạn latency, memory, hardware và submission rate.
- NLTK/package version dùng trong môi trường chấm METEOR nếu không được pin ngoài artifact hiện có.

### Must verify trước benchmark chính thức

- Raw-data, split và corpus manifests/fingerprints; kiểm tra leakage theo task semantics.
- Canonical source integrity, parser boundary quality và deterministic chunk regeneration.
- Gold-document distribution, label-completeness signals và ceiling do tối đa năm output.
- Mapping chunk → document → source, deduplication và hành vi với ID sai/missing/extra.
- Sự nhất quán giữa indexing/query encoding, gồm tokenizer và `max_seq_length`.
- Gold-evidence mapping của LegalQA trước khi gọi một run là oracle.
- Local scorer reproduction phải gọi hoặc tái sử dụng trung thực organizer scorer.

## Tiêu chí thành công của research baseline

Baseline đạt mục đích khi artifact tái lập được trả lời:

1. Gold bị mất ở candidate retrieval hay ở document construction/reranking/final selection?
2. Retriever mới recover gold độc nhất hay chủ yếu lặp lại candidate cũ?
3. Với LegalQA, khoảng cách giữa control khả dụng và retrieved-evidence nằm ở retrieval, evidence selection, generation/grounding hay output formatting?
4. Corpus representation có làm mất source coverage, provenance hoặc tạo truncation trước các tầng downstream không?
