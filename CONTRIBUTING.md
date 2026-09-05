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

## 2. Quản lý Dữ liệu và Model Weights

- **KHÔNG push file dữ liệu lớn lên Github**. Mọi file dữ liệu phải được lưu trong thư mục `data/` (thư mục này đã được đưa vào `.gitignore`).
- **KHÔNG push model weights** (`.bin`, `.pt`, `.h5`, v.v.). Nếu cần chia sẻ model, hãy up lên Google Drive/Hugging Face và gửi link.
- Chỉ push code (file `.py`, `.md`, `.txt`, `.ipynb` nhưng lưu ý clear output của `.ipynb` trước khi push nếu quá nặng).

## 3. Cài đặt Thư viện

- Bất cứ khi nào bạn chạy `pip install <thư-viện>`, bạn phải cập nhật file `requirements.txt`:
  - Lệnh: `pip freeze > requirements.txt` (hoặc thêm thủ công vào file).
- Báo cho team biết để mọi người chạy lại `pip install -r requirements.txt` trên máy của họ.

## 4. Phân công Công việc Tham khảo

- **Data Engineer**: Xử lý `src/parser.py`, `src/schema.py` và các file trong `notebooks/`.
- **Text Processor**: Xử lý `src/chunker.py` (cắt luật theo điều khoản).
- **Retrieval Engineer**: Xử lý `src/embedder.py`, `src/index_loader.py` (Cài đặt BM25, FAISS).
- **Evaluator**: Xử lý `src/validator.py`, `src/metrics.py`.
- **System Integrator**: Xử lý luồng chính trong `src/pipeline.py` và `main.py`.

Chúc cả nhóm làm việc hiệu quả và chinh phục giải thưởng DSC 2026! 🚀
