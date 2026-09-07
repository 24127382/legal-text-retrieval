# 01 — Bài toán và mục tiêu

## Hai task, một evidence bottleneck

**LegalIR** nhận một truy vấn pháp lý tiếng Việt và xếp hạng `document_id` liên quan. **LegalQA** nhận một câu hỏi, tìm căn cứ, rồi sinh câu trả lời ngắn, đúng và được evidence hỗ trợ.

```text
query/question
      ↓
evidence retrieval (shared)
      ↓
candidate pool
      ├─ LegalIR: reranking → final selection → document IDs
      └─ LegalQA: evidence selection → generation → verification → answer
```

Hai task không nên được xây như hai hệ độc lập vì cùng chịu một **evidence bottleneck**: nếu tài liệu đúng không vào candidate pool, reranker và generator đều không thể khôi phục nó. Ngược lại, nếu evidence đã có nhưng LegalQA vẫn sai thì lỗi nằm ở evidence selection, reasoning, grounding hoặc answer realization; thay retriever lúc đó có thể không giải quyết đúng nguyên nhân.

## Mục tiêu nghiên cứu

### LegalIR

1. Tối đa hóa candidate coverage bằng các tín hiệu bổ sung nhau.
2. Đo candidate recall trước khi tối ưu reranking.
3. Chuyển chunk-level retrieval thành document-level ranking có kiểm soát.
4. Phân bổ đúng tối đa 5 vị trí output bằng final selection/calibration.
5. Thay đổi một major research axis tại một thời điểm.

### LegalQA

1. Tái sử dụng evidence retrieval đã đo được của LegalIR.
2. Dùng oracle experiment để tách retrieval error khỏi generation error.
3. Chọn evidence đủ và đúng trước khi tăng reasoning depth.
4. Chỉ tối ưu format theo metric sau khi factual support được kiểm soát.

## Điều đang biết về metric

Source research ghi nhận:

- LegalIR dùng Recall làm metric chính, Precision để phân hạng khi Recall bằng nhau, và output tối đa 5 `document_id` mỗi query; vi phạm giới hạn có thể làm điểm query bằng 0.
- LegalQA dùng METEOR làm metric chính và ROUGE-L làm metric phụ.

Các điểm trên phải được đối chiếu lại với rules và scorer hiện hành trước khi đóng băng protocol. Cho đến khi có scorer artifact/version cụ thể, tài liệu này gọi Recall@5, Precision, METEOR và ROUGE-L là **reported competition metrics**, không tuyên bố implementation cục bộ tương đương official scorer.

## Known / Unknown / Must Verify

### Known

- Hai task dùng chung miền văn bản pháp luật tiếng Việt và có thể chia sẻ retrieval stack.
- `main` có parser, structure-aware chunker, BGE-M3 dense embedding và FAISS chunk retrieval.
- Existing docs báo cáo corpus khoảng 8,5k documents và khoảng 94,7k chunks.
- Source research báo cáo LegalIR giới hạn tối đa 5 document IDs và ưu tiên Recall.
- Code hiện tại dừng ở chunk retrieval; chưa có document-level final selection.

### Unknown

- Số query train/public/private.
- Phân bố số relevant documents trên mỗi query.
- Relevance labels có exhaustive hay không.
- Phân bố độ dài document thực tế và độ dài sau tokenizer.
- Mức đầy đủ/chính xác của metadata schema.
- Có metadata phiên bản, ngày hiệu lực, sửa đổi, bãi bỏ hay không.
- Quy tắc external model, external data và external API.
- Latency, memory, hardware hoặc submission-rate constraints.
- Exact normalization/tokenization của scorer LegalQA.

### Must Verify trước baseline chính thức

- Rules/scorer hiện hành: giới hạn output, duplicate IDs, order sensitivity, cách tính Recall/Precision và hành vi khi `|G_q| > 5`.
- Train/dev split chống leakage; public leaderboard không phải validation set duy nhất.
- Gold-document distribution và dấu hiệu label incompleteness.
- Mapping ổn định từ chunk ID về document ID và xử lý duplicate chunks.
- Sự nhất quán giữa encoding lúc index và lúc query, gồm `max_seq_length`.
- Corpus counts 8.512/94.717 từ artifact tái tạo được, không chỉ từ báo cáo.
- Metadata title/hierarchy/version có đủ chất lượng để dùng feature hoặc filter.

## Tiêu chí thành công của research baseline

Baseline đạt mục đích khi nó trả lời được ba câu hỏi bằng số liệu:

1. Gold bị mất ở candidate retrieval hay bị misorder ở reranking/final selection?
2. Mỗi retriever mới có recover gold độc nhất hay chỉ lặp lại cùng candidate?
3. Với LegalQA, khoảng cách giữa oracle-evidence và retrieved-evidence nằm ở retrieval, evidence selection hay generation?
