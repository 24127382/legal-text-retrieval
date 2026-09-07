# Research documentation — UIT DSC 2026 LegalIR / LegalQA

## Mục đích

Bộ tài liệu này là research contract cho hai bài toán dùng chung một tầng bằng chứng:

```text
LegalIR: lexical retrieval → semantic retrieval → hybrid/fusion
         → fine-grained reranking → final document selection

LegalQA: LegalIR evidence → evidence selection → grounded generation
         → verification → metric-aware answer realization
```

Mục tiêu của baseline không phải đạt điểm cao nhất ngay lập tức. Mục tiêu là tạo một hệ đo lường cho biết **thành phần nào đáng nhận thí nghiệm tiếp theo**. Tài liệu này không xác nhận một phương pháp đã được triển khai nếu code trên branch hiện tại không có phương pháp đó.

## Quy ước trạng thái

| Nhãn | Nghĩa |
|---|---|
| `Implemented` | Có code trên branch `docs/method-research-baseline`, kế thừa từ `main`. |
| `Existing branch` | Có code trên branch khác; chưa được merge và chưa thuộc baseline hiện tại. |
| `Planned` | Đã có experiment ID và điều kiện đánh giá. |
| `Research candidate` | Có cơ sở để khảo sát nhưng chưa được xếp vào lượt chạy gần nhất. |
| `Speculative` | Rủi ro/chi phí cao hoặc bằng chứng hiện tại chưa đủ. |

## Thứ tự đọc

1. [`01_problem_and_objectives.md`](01_problem_and_objectives.md) — bài toán, evidence bottleneck và các điều chưa biết.
2. [`02_method_space.md`](02_method_space.md) — taxonomy LegalIR/LegalQA và compatibility.
3. [`03_baseline_design.md`](03_baseline_design.md) — ladder B0 → B1 → B2 → B3.
4. [`04_evaluation_and_diagnostics.md`](04_evaluation_and_diagnostics.md) — metric theo tầng, gold distribution và error analysis.
5. [`05_experiment_map.md`](05_experiment_map.md) — ma trận thí nghiệm và nơi ghi kết quả.
6. [`06_legalqa_strategy.md`](06_legalqa_strategy.md) — chiến lược QA dựa trên bằng chứng từ LegalIR.
7. [`07_research_roadmap.md`](07_research_roadmap.md) — roadmap có điều kiện GO / NO-GO.
8. [`08_references.md`](08_references.md) — tài liệu tham khảo đã chuẩn hóa.

## Trạng thái repository tại thời điểm tạo tài liệu

### Implemented trên `main`

- Legal parsing và metadata cấu trúc (`part`, `chapter`, `section`, `article`, `clause`, `point`).
- Structure-aware chunking với ranh giới cấu trúc, giới hạn kích thước và invariant không mất text.
- BGE-M3 dense embedding, vector chuẩn hóa L2 và FAISS `IndexFlatIP` ở mức chunk.
- `HFLegalRetriever` tải FAISS index và mapping từ Hugging Face, rồi trả về top-k **chunks**.
- Helper cục bộ cho Recall@K và MRR ở mức danh sách document ID.

### Existing branch, không thuộc branch hiện tại

- `origin/feature/bm25`: lớp tạo `BM25Okapi` tối thiểu từ chunk text.
- `origin/version-1`: BM25 builder, dense + BM25 RRF, evaluation/submission prototype.
- `origin/ver2`: tiếp tục prototype trên và thêm cross-encoder reranking.

Không branch nào ở trên được merge hoặc sửa trong task tài liệu này. Chúng là bằng chứng tồn tại, không phải bằng chứng đã được benchmark, productionize hay tích hợp vào `main`.

### Planned baseline

Baseline mạnh được khuyến nghị là **B2: BM25 + BGE-M3 dense → union → alpha fusion hoặc RRF → cross-encoder → document-level ranking → tối đa 5 document IDs**. Đây là kiến trúc đề xuất, chưa phải mô tả hệ thống đang chạy. Chi tiết ở [`03_baseline_design.md`](03_baseline_design.md).

## Repository observations

1. Repository hiện retrieve chunk nhưng output cuộc thi là document ID. Chưa có document aggregation trong `main`; đây là research axis bắt buộc, không phải chi tiết hậu xử lý.
2. `docs/preprocess_chunking_faiss.md` báo cáo 8.512 documents và 94.717 chunks với QC không lỗi. Repository không chứa artifact dữ liệu để tái kiểm tra trong task này, vì vậy các số này là **reported, not independently verified**.
3. Tài liệu hiện có nói BGE-M3 hỗ trợ context 8.192 tokens, trong khi `HFLegalRetriever` đặt `model.max_seq_length = 1024`; indexing path không đặt cùng giới hạn một cách tường minh. Cần kiểm tra tính nhất quán query/document encoding trước khi benchmark.
4. `docs/embedding.py` nêu latency online 10–30 ms nhưng không kèm benchmark artifact; coi đây là target chưa xác minh.
5. `src/metrics.py` chỉ có helper Recall@K và MRR, chưa phải bản sao official scorer, chưa có Precision chính thức, candidate-pool diagnostics hay xử lý giới hạn output.
6. `main` chưa có BM25, fusion, reranking, final top-k calibration, LegalQA generation hoặc verifier.
7. Phần cuối `.gitignore` chứa một pattern bị mã hóa NUL mà Git diễn giải như `*`, nên mọi file untracked bị ignore. Task này không sửa `.gitignore`; các file nghiên cứu phải được stage tường minh bằng `git add -f`.

## Ghi kết quả ở đâu

Mỗi lần chạy phải cập nhật hàng tương ứng trong [`05_experiment_map.md`](05_experiment_map.md) và thêm một record theo mẫu:

```markdown
### E__ / run YYYY-MM-DD-name
- Commit / config / data split / seed:
- Control và independent variable:
- Candidate Recall@10/20/50/100/200:
- Final Recall@5 / Precision / diagnostics:
- Candidate overlap và unique gold (nếu có nhiều retriever):
- Error categories cải thiện / hồi quy:
- Compute, latency, index size:
- Kết luận GO / NO-GO và thí nghiệm kế tiếp:
```

Không thay số liệu cũ bằng số liệu mới; thêm run mới để giữ audit trail.
