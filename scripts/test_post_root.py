import requests

url = "https://vbpl.vn/"
payload = {
 "pageNumber": 1,
 "pageSize": 10,
 "searchMode": "All",
 "keyword": "đèn đỏ"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0",
    "Content-Type": "application/json"
}

try:
    r = requests.post(url, json=payload, headers=headers)
    print("Status:", r.status_code)
    print("Headers:", r.headers)
    print("Content:", r.text[:500])
except Exception as e:
    print(e)
