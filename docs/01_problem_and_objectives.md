# 01 — Bài toán và mục tiêu

## Hai task, một evidence bottleneck

**LegalIR** (Legal Information Retrieval — truy hồi thông tin pháp luật) nhận một câu hỏi pháp lý và chọn các ID văn bản liên quan. **LegalQA** (Legal Question Answering — hỏi đáp pháp luật) nhận câu hỏi, tìm căn cứ rồi tạo câu trả lời. Hai task cùng chịu một **evidence bottleneck**: nếu văn bản cần thiết không vào candidate pool (tập ứng viên), reranker và generator không thể khôi phục bằng chứng bị thiếu.

```text
question
   ↓
evidence retrieval
   ↓
candidate pool
   ├─ LegalIR: document construction → aggregation/reranking → final subset
   └─ LegalQA: evidence selection → grounded generation → verification → answer
```

Ngược lại, nếu evidence đã có nhưng LegalQA vẫn sai, lỗi có thể nằm ở chọn đoạn, suy luận, grounding (ràng buộc câu trả lời vào bằng chứng) hoặc answer realization (cách diễn đạt đầu ra). Thay retriever khi đó không nhất thiết giải đúng nguyên nhân.

## Mục tiêu nghiên cứu

### LegalIR

1. Tối đa hóa candidate coverage bằng các tín hiệu truy hồi bổ sung nhau.
2. Đo candidate recall trước khi tối ưu reranking.
3. Phân biệt rõ chunk retrieval, candidate document construction, document aggregation, reranking và final subset selection.
4. Dùng tối đa năm vị trí output theo đúng scorer chính thức.
5. Chỉ thay đổi một major research axis trong mỗi thí nghiệm để giữ attribution.

### LegalQA

1. Tái sử dụng tầng evidence retrieval đã được đo của LegalIR.
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

Các JSON hiện có trong `data/LegalIR/` và `data/LegalQA/` đều là object keyed theo sample ID:

- LegalIR train: value có `question` và `answer`, trong đó `answer` là list document ID; public-official giữ cùng hai field và để `answer: null`.
- LegalQA train: value có `question` và `answer`, trong đó `answer` là chuỗi; public-official giữ cùng hai field và để `answer: null`.

Đây là quan sát trên dữ liệu hiện có, không phải tuyên bố về mọi split hoặc mọi phiên bản tương lai.

## Known / Unknown / Must Verify

### Known

- Official scorer contract và tên output metric đã có trong `scoring/`.
- LegalIR và LegalQA có thể chia sẻ tầng retrieval nhưng có submission adapter khác nhau.
- Code trong `src/` có parser/chunker và prototype dense chunk retrieval; đây là `Code present`, không phải `Validated` hay `Benchmarked`.
- B2 trong tài liệu là reference design `Planned`, không phải hệ thống đã hoàn thành.

### Unknown

- Quy mô và quan hệ chính xác của train/dev/public/private ngoài các file hiện có.
- Phân bố số gold document mỗi query và mức đầy đủ của relevance labels.
- Mapping gold evidence cho LegalQA có tồn tại và đủ tin cậy cho oracle hay không.
- Độ dài document/chunk sau tokenizer, chất lượng metadata và thông tin phiên bản/hiệu lực.
- Quy tắc external model/data/API; giới hạn latency, memory, hardware và submission rate.
- NLTK/package version dùng trong môi trường chấm METEOR nếu không được pin ngoài artifact hiện có.

### Must verify trước benchmark chính thức

- Split manifest/fingerprint và kiểm tra leakage.
- Gold-document distribution, label-completeness signals và ceiling do tối đa năm output.
- Mapping chunk → document, deduplication và hành vi với ID sai/missing/extra.
- Sự nhất quán giữa indexing/query encoding, gồm tokenizer và `max_seq_length`.
- Gold-evidence mapping của LegalQA trước khi gọi một run là oracle.
- Local scorer reproduction phải gọi hoặc tái sử dụng trung thực organizer scorer.

## Tiêu chí thành công của research baseline

Baseline đạt mục đích khi artifact tái lập được trả lời:

1. Gold bị mất ở candidate retrieval hay ở document construction/reranking/final selection?
2. Retriever mới recover gold độc nhất hay chủ yếu lặp lại candidate cũ?
3. Với LegalQA, khoảng cách giữa control khả dụng và retrieved-evidence nằm ở retrieval, evidence selection, generation/grounding hay output formatting?
