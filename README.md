# Legal Text Retrieval — UIT Data Science Challenge 2026

Repository nghiên cứu hai bài toán pháp luật tiếng Việt có chung nút thắt bằng chứng:

- **Legal Information Retrieval (LegalIR)**: tìm tập văn bản pháp luật liên quan cho một câu hỏi.
- **Legal Question Answering (LegalQA)**: tạo câu trả lời từ câu hỏi và bằng chứng pháp lý.

Định hướng chung là đo riêng độ bao phủ của truy hồi, chất lượng xếp hạng/chọn bằng chứng và chất lượng sinh câu trả lời. Việc có code cho một thành phần không được xem là bằng chứng thành phần đó đã được kiểm chứng hoặc benchmark.

## Tài liệu nghiên cứu

| Tài liệu | Nội dung |
|---|---|
| [01 — Bài toán và mục tiêu](docs/01_problem_and_objectives.md) | Phạm vi, evidence bottleneck và các điều đã biết/chưa biết. |
| [02 — Không gian phương pháp](docs/02_method_space.md) | Taxonomy LegalIR/LegalQA và vị trí của từng hướng nghiên cứu. |
| [03 — Thiết kế baseline](docs/03_baseline_design.md) | Ladder B0 → B1 → B2 → B3 và các tầng quyết định. |
| [04 — Evaluation và diagnostics](docs/04_evaluation_and_diagnostics.md) | Hợp đồng scoring chính thức và diagnostics nội bộ. |
| [05 — Experiment map](docs/05_experiment_map.md) | Ma trận thí nghiệm LegalIR/LegalQA và run log. |
| [06 — Chiến lược LegalQA](docs/06_legalqa_strategy.md) | Oracle, retrieve–rerank–generate, evidence selection và verification. |
| [07 — Research roadmap](docs/07_research_roadmap.md) | Lộ trình có điều kiện GO / NO-GO. |
| [08 — Tài liệu tham khảo](docs/08_references.md) | Nguồn hỗ trợ cho research contract. |

LegalIR tạo nền tảng bằng chứng cho LegalQA, nhưng các control LegalQA có thể chạy sớm khi đủ đầu vào; không cần chờ toàn bộ roadmap LegalIR hoàn tất.

## Đóng góp

Đọc [CONTRIBUTING.md](CONTRIBUTING.md) trước khi đóng góp. Các thay đổi nghiên cứu cần ghi rõ giả thuyết, control, dữ liệu/split, metric và trạng thái (`Code present`, `Validated`, `Benchmarked`, `Planned`, `Research candidate` hoặc `Speculative`).
