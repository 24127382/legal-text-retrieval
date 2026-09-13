# Hướng dẫn Đóng góp (Contributing Guidelines)

Chào mừng các bạn đến với repository của nhóm! Để đảm bảo source code luôn sạch sẽ, tránh conflict và dễ dàng review, mọi người VUI LÒNG tuân thủ các quy tắc sau:

## 1. Quy tắc Git Workflow (BẮT BUỘC)

- **Tuyệt đối KHÔNG commit trực tiếp vào nhánh `main`**.
- Khi bắt tay vào làm một task mới, hãy tạo một nhánh (branch) riêng từ nhánh `main`.
  - Cú pháp: `git checkout -b <loại>/<tên-chức-năng>`
  - Ví dụ: `git checkout -b feature/data-parser`, `git checkout -b fix/chunk-bug`, `git checkout -b eda/data-exploration`.
- Khi làm xong, push nhánh của bạn lên Github: `git push origin <tên-nhánh-của-bạn>`.
- Lên Github tạo **Pull Request (PR)**.
- Gắn thẻ (tag) ít nhất **1 thành viên khác** vào để **Code Review**.
- Chỉ khi người review Approve (chấp thuận), bạn mới được phép Merge PR vào nhánh `main`.

## 2. Execution model

- `docs/` giữ research reasoning và experiment evidence; `notebooks/` giữ executable experiment/inference artifacts.
- Notebook phải standalone: không import `src`, không dựa vào repository checkout và không tách implementation sang một local Python package dùng chung.
- Target runtime là Kaggle với Internet disabled. Chỉ dùng package đã có trong runtime hoặc offline wheel được attach qua Kaggle Input và cài bằng `--no-index`.
- Dataset, model snapshot, tokenizer và resource khác phải được attach rõ ràng dưới `/kaggle/input/...`. Luôn load model từ local path với local-only mode; thiếu file phải fail loudly, không download hoặc fallback sang network.
- Schema, provenance, unique IDs, candidate universe, finite scores, deterministic ranking và output format phải được kiểm tra bằng assertion/sanity-check cells trong notebook.

## 3. Repository boundaries

- `scoring/LegalIR/` và `scoring/LegalQA/` là immutable organizer artifacts; không cleanup hoặc refactor.
- Project-authored `.py` chỉ được dùng cho minimal submission packaging trong `tools/`. Không tạo lại runtime research library dưới `src/`, `lib/`, `common/`, `utils/`, `core/` hoặc `pipeline/`.
- Không duy trì test suite Python riêng chỉ để test notebook implementation. Đặt experiment-level tests cạnh implementation trong notebook.

## 4. Dữ liệu và artifacts

- Không đưa raw data, Kaggle datasets, model/tokenizer weights, indexes, embeddings, chunk/prediction dumps, ZIP submission hoặc output experiment lớn vào Git.
- Notebook outputs chỉ được giữ khi cần làm evidence nhỏ, reviewable; kết quả nghiên cứu phải được tóm tắt trung thực trong `docs/research_log.md`.
- Utility packaging chỉ validate prediction đã có và tạo ZIP; không inference, không sửa semantic output và không tự đặt organizer filename.

Chúc cả nhóm làm việc hiệu quả và chinh phục giải thưởng DSC 2026! 🚀
