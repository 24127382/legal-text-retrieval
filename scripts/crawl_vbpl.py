import requests
import time
import random
import json
import os

def crawl_vbpl_metadata():
    # 1. Cấu hình URL và Header cho kiến trúc Next.js mới
    api_url = "https://vbpl.vn/"
    output_file = "vbpl_metadata_raw.jsonl"
    
    # Đây là các header bí mật bắt buộc phải có để giả lập Server Action của Next.js
    headers = {
        "accept": "text/x-component",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "content-type": "text/plain;charset=UTF-8",
        "next-action": "c529d164f28418e5898a834422629e64c6816af1",
        "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
    }
    
    # Số trang dự kiến cào (bạn có thể tăng lên nếu muốn cào hết)
    total_pages = 2400
    page_size = 10
    
    # 2. TỰ ĐỘNG KHÔI PHỤC (Auto-Resume)
    start_page = 1
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            lines_count = sum(1 for _ in f)
            # Tính toán trang bắt đầu dựa trên số dòng đã cào
            start_page = (lines_count // page_size) + 1
            print(f"[*] Phát hiện file cũ có {lines_count} văn bản.")
            print(f"[*] Tự động tiếp tục cào từ trang {start_page}...")
    
    print(f"Bắt đầu quá trình thu thập với API Next.js. Tổng số trang dự kiến: {total_pages}...")
    
    # 3. Vòng lặp thu thập an toàn
    for current_page in range(start_page, total_pages + 1):
        # Payload dạng mảng 1 phần tử theo chuẩn Next.js Server Action
        payload_array = [{
            "pageNumber": current_page,
            "pageSize": page_size,
            "keyword": "", # Để rỗng để cào tất cả
            "optionDoc": "title",
            "matchMode": "all_words"
        }]
        
        try:
            # Gửi request lấy dữ liệu (phải dùng json.dumps vì content-type là text/plain)
            response = requests.post(api_url, data=json.dumps(payload_array), headers=headers, timeout=15)
            
            # Kiểm tra trạng thái phản hồi
            if response.status_code == 200:
                response.encoding = 'utf-8' # Tránh lỗi Mojibake
                text_response = response.text
                items = []
                
                # Bóc tách dữ liệu từ định dạng RSC của Next.js
                for line in text_response.split('\n'):
                    if '"items":' in line:
                        start_idx = line.find('{')
                        if start_idx != -1:
                            try:
                                data = json.loads(line[start_idx:])
                                items = data.get('items', [])
                            except json.JSONDecodeError:
                                pass
                            break
                            
                if not items:
                    print(f"Trang {current_page}: Không có dữ liệu, có thể đã hết danh sách (Hoặc API ID đã bị đổi).")
                    break # Thoát vòng lặp nếu không có dữ liệu
                    
                # 3. LƯU CUỐN CHIẾU (Checkpointing)
                # Mở file ở chế độ 'a' (append) để ghi nối tiếp vào cuối file
                with open(output_file, 'a', encoding='utf-8') as f:
                    for item in items:
                        # Ghi từng item thành 1 dòng json độc lập (chuẩn JSONL)
                        json.dump(item, f, ensure_ascii=False)
                        f.write('\n')
                        
                print(f"Đã cào và lưu thành công trang {current_page}/{total_pages} ({len(items)} văn bản).")
            else:
                print(f"Lỗi ở trang {current_page}: Status Code {response.status_code}")
                # Nếu trả về 405 hoặc mã khác, có thể Next-Action ID đã hết hạn
                
        except Exception as e:
            print(f"Lỗi kết nối hoặc ngoại lệ ở trang {current_page}: {e}")
            time.sleep(5)
            
        # 4. CHỐNG BỊ CHẶN (Politeness)
        sleep_time = random.uniform(1.5, 3.5)
        time.sleep(sleep_time)
        
    print("Hoàn tất quá trình cào dữ liệu!")

if __name__ == "__main__":
    # open("vbpl_metadata_raw.jsonl", 'w').close() # Bỏ comment nếu muốn xóa file cũ đi cào lại
    crawl_vbpl_metadata()
