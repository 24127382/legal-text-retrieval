# Legal Text Retrieval — UIT Data Science Challenge 2026

Repository nghiên cứu pháp luật tiếng Việt theo ba layer phụ thuộc nhau:

- **Data & Corpus Representation**: bảo toàn, kiểm tra và biểu diễn corpus thành evidence units có provenance.
- **Legal Information Retrieval (LegalIR)**: tìm tập văn bản pháp luật liên quan cho một câu hỏi.
- **Legal Question Answering (LegalQA)**: tạo câu trả lời từ câu hỏi và bằng chứng pháp lý.

Luồng nghiên cứu là `Data & Corpus Representation → LegalIR → LegalQA`. Định hướng chung là đo riêng chất lượng corpus/evidence unit, độ bao phủ truy hồi, xếp hạng/chọn bằng chứng và sinh câu trả lời. Việc có code cho một thành phần không được xem là bằng chứng thành phần đó đã được kiểm chứng hoặc benchmark.

## Tài liệu nghiên cứu

| Tài liệu | Nội dung |
|---|---|
| [00 — Data contract và preprocessing](docs/00_data_contract_and_preprocessing.md) | Contract từ raw data đến canonical corpus, provenance và integrity gates. |
| [01 — Bài toán và mục tiêu](docs/01_problem_and_objectives.md) | Phạm vi, evidence bottleneck và các điều đã biết/chưa biết. |
| [02 — Không gian phương pháp](docs/02_method_space.md) | Taxonomy Data & Corpus, LegalIR, LegalQA và dependencies. |
| [03 — Thiết kế baseline](docs/03_baseline_design.md) | Ladder C0 → B0 → B1 → B2 → B3 và các tầng quyết định. |
| [04 — Evaluation và diagnostics](docs/04_evaluation_and_diagnostics.md) | Hợp đồng scoring chính thức và diagnostics nội bộ. |
| [05 — Experiment map](docs/05_experiment_map.md) | P00, D00–D06, LegalIR/LegalQA experiments và run log. |
| [06 — Chiến lược LegalQA](docs/06_legalqa_strategy.md) | Oracle, retrieve–rerank–generate, evidence selection và verification. |
| [07 — Research roadmap](docs/07_research_roadmap.md) | Lộ trình có điều kiện GO / NO-GO. |
| [08 — Tài liệu tham khảo](docs/08_references.md) | Nguồn hỗ trợ cho research contract. |

Canonical corpus tạo nền tảng cho LegalIR và evidence-grounded LegalQA. QA0 closed-book, và gold-evidence oracle khi mapping đã được verify, có thể chạy theo dependency riêng.

## Execution workflow

```text
research design trong docs/
        ↓
standalone offline Kaggle notebook
        ↓
experiment result hoặc prediction JSON
        ↓
evidence trong docs/research_log.md
        ↓
minimal submission packaging
```

`notebooks/` là nơi chứa executable experiment/inference artifacts. Mỗi notebook phải self-contained, không import `src` hoặc phụ thuộc vào repository checkout, và phải chạy được khi Kaggle Internet bị tắt. Notebook chỉ được dùng package có sẵn trong Kaggle runtime hoặc file được attach rõ ràng qua Kaggle Input. Model/tokenizer phải được load từ path local dạng `/kaggle/input/<attached-model-dataset>/...`, với offline/local-only mode; thiếu resource phải dừng bằng lỗi rõ ràng, không fallback sang network.

`scoring/` là organizer-provided authority và không được refactor. Project-authored Python chỉ giới hạn ở utility đóng gói submission trong `tools/`; mọi implementation phục vụ preprocessing, retrieval, reranking, inference và experiment-level sanity checks phải nằm trực tiếp trong notebook.

Để đóng gói một prediction JSON đã được notebook tạo:

```text
python tools/package_submission.py path/to/<organizer_expected_filename>.json submission.zip
```

Tên JSON phải lấy từ sample submission hoặc phase instructions chính thức; utility giữ nguyên basename và đặt file trực tiếp ở root của ZIP.

## Đóng góp

Đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi đóng góp. Các thay đổi nghiên cứu cần ghi rõ giả thuyết, control, dữ liệu/split, metric và trạng thái (`Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate` hoặc `Speculative`).
