# Legal Text Retrieval — UIT Data Science Challenge 2026

Repository này phục vụ nghiên cứu và phát triển cho hai bài toán liên quan chặt chẽ trong miền pháp luật tiếng Việt: **Legal Information Retrieval** (truy hồi thông tin pháp luật) và **Legal Question Answering** (hỏi đáp pháp luật). Mục tiêu chung là xây dựng một quy trình có thể tìm đúng căn cứ pháp lý, đánh giá rõ từng nguồn sai số và dùng bằng chứng đó để hỗ trợ câu trả lời đáng tin cậy.

README này chỉ giới thiệu định hướng tổng quát của dự án. Các giả thuyết, thiết kế baseline, protocol đánh giá và lộ trình thí nghiệm được trình bày trong bộ [tài liệu nghiên cứu](docs/README.md).

## Bài toán

### LegalIR

**Legal Information Retrieval (LegalIR)** nhận một câu hỏi pháp lý và trả về ID của các văn bản có liên quan nhất:

```text
question
   ↓
retrieve relevant legal documents
   ↓
document IDs
```

Mục tiêu là xác định đúng các văn bản pháp luật cung cấp căn cứ cho câu hỏi, đồng thời xếp hạng chúng trong số lượng vị trí output có hạn. Ở cấp độ nghiên cứu, LegalIR được xem là bài toán tìm và lựa chọn evidence — tức bằng chứng hoặc căn cứ pháp lý — trước khi một hệ thống có thể suy luận hay tạo câu trả lời.

### LegalQA

**Legal Question Answering (LegalQA)** sử dụng câu hỏi và evidence pháp lý để tạo câu trả lời:

```text
question
   ↓
retrieve legal evidence
   ↓
reason over evidence
   ↓
answer
```

Chất lượng LegalQA phụ thuộc mạnh vào evidence do LegalIR cung cấp. Nếu văn bản cần thiết không xuất hiện trong candidate pool (tập ứng viên), các bước chọn evidence, reasoning và generation phía sau khó có thể khôi phục căn cứ bị thiếu.

> **LegalIR is the evidence retrieval foundation for LegalQA.**

## Mục tiêu nghiên cứu

### LegalIR

1. Tối đa hóa candidate coverage bằng các retrieval signals bổ sung nhau.
2. Đo candidate recall trước khi tối ưu reranking.
3. Chuyển chunk-level retrieval thành document-level ranking có kiểm soát.
4. Phân bổ đúng tối đa 5 vị trí output bằng final selection/calibration.
5. Thay đổi một major research axis tại một thời điểm.

> Mục tiêu của LegalIR không chỉ là tìm một model retrieval mạnh, mà là xây một pipeline có thể đo được bottleneck giữa candidate retrieval, ranking và final selection.

### LegalQA

1. Tái sử dụng evidence retrieval đã đo được của LegalIR.
2. Dùng oracle experiment để tách retrieval error khỏi generation error.
3. Chọn evidence đủ và đúng trước khi tăng reasoning depth.
4. Chỉ tối ưu format theo metric sau khi factual support được kiểm soát.

> Với LegalQA, evidence quality được xem là yếu tố đặt trần cho factual correctness trước khi tối ưu reasoning hoặc answer generation.

## Hướng nghiên cứu tổng quát

Luồng nghiên cứu LegalIR tập trung trước hết vào độ bao phủ của candidate pool, sau đó mới tối ưu thứ hạng và quyết định output cuối cùng:

```text
lexical retrieval
        +
semantic retrieval
        ↓
candidate retrieval
        ↓
fusion / reranking
        ↓
document-level ranking
        ↓
final selection
```

LegalQA tiếp tục từ evidence đã được LegalIR truy hồi và đánh giá:

```text
LegalIR
   ↓
evidence retrieval
   ↓
evidence selection
   ↓
grounded reasoning / generation
   ↓
answer
```

Đây là các luồng khái niệm dùng để tổ chức nghiên cứu, không phải tuyên bố rằng mọi thành phần đã được triển khai.

## Tài liệu nghiên cứu

Các tài liệu nghiên cứu hiện nằm trực tiếp trong thư mục [`docs/`](docs/README.md):

| Tài liệu | Nội dung |
|---|---|
| [`docs/README.md`](docs/README.md) | Chỉ mục, quy ước trạng thái và thứ tự đọc bộ tài liệu. |
| [`docs/01_problem_and_objectives.md`](docs/01_problem_and_objectives.md) | Định nghĩa hai bài toán, evidence bottleneck và mục tiêu nghiên cứu. |
| [`docs/02_method_space.md`](docs/02_method_space.md) | Không gian phương pháp và nguyên tắc chọn hướng thí nghiệm. |
| [`docs/03_baseline_design.md`](docs/03_baseline_design.md) | Thiết kế baseline và các tầng quyết định của LegalIR. |
| [`docs/04_evaluation_and_diagnostics.md`](docs/04_evaluation_and_diagnostics.md) | Evaluation, diagnostics và cách xác định bottleneck. |
| [`docs/05_experiment_map.md`](docs/05_experiment_map.md) | Bản đồ giả thuyết, experiment controls và nơi ghi kết quả. |
| [`docs/06_legalqa_strategy.md`](docs/06_legalqa_strategy.md) | Chiến lược LegalQA dựa trên evidence từ LegalIR. |
| [`docs/07_research_roadmap.md`](docs/07_research_roadmap.md) | Lộ trình nghiên cứu theo các decision gate. |
| [`docs/08_references.md`](docs/08_references.md) | Danh mục nguồn tham khảo cho các tài liệu nghiên cứu. |

## Cách đọc repository

Thứ tự đọc khuyến nghị cho luồng LegalIR:

[`Problem & Objectives`](docs/01_problem_and_objectives.md) → [`Method Space`](docs/02_method_space.md) → [`Baseline Design`](docs/03_baseline_design.md) → [`Evaluation`](docs/04_evaluation_and_diagnostics.md) → [`Experiment Map`](docs/05_experiment_map.md) → [`Research Roadmap`](docs/07_research_roadmap.md)

Khi chuyển sang LegalQA, đọc tiếp [`LegalQA Strategy`](docs/06_legalqa_strategy.md). Danh mục đầy đủ và trạng thái của từng tài liệu được duy trì tại [`docs/README.md`](docs/README.md).

## Nguyên tắc nghiên cứu

> Một retriever mới chỉ có giá trị nếu nó tăng candidate coverage hoặc tạo complementary errors.

> Reranker không thể cứu một gold document chưa từng lọt vào candidate pool.

> Không thay nhiều major research axes cùng lúc nếu muốn biết improvement đến từ đâu.

> Với LegalQA, phải tách retrieval error khỏi generation error trước khi tối ưu hệ thống.

## Contributing

Xem [`CONTRIBUTING.md`](CONTRIBUTING.md) trước khi đóng góp. Contributors cần tuân theo Git workflow của repository: tạo branch riêng cho từng task và không làm việc trực tiếp trên `main`.
