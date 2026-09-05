import requests
import json

url = "https://vbpl.vn/"
headers = {
    "accept": "text/x-component",
    "content-type": "text/plain;charset=UTF-8",
    "next-action": "c529d164f28418e5898a834422629e64c6816af1",
    "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
}

payload_array = [{
    "pageNumber": 1,
    "pageSize": 10,
    "keyword": "đèn đỏ",
    "optionDoc": "title",
    "matchMode": "all_words"
}]

# Send as text/plain
r = requests.post(url, data=json.dumps(payload_array), headers=headers)
print("Status:", r.status_code)
# Try to decode content
if r.status_code == 200:
    text = r.text
    # find the line with items
    for line in text.split('\n'):
        if '"items":' in line:
            # slice out the starting "1:" or whatever
            start_idx = line.find('{')
            if start_idx != -1:
                data = json.loads(line[start_idx:])
                print(f"Total found: {data.get('total')}")
                print(f"Items length: {len(data.get('items', []))}")
                if data.get('items'):
                    print(f"First item title: {data['items'][0].get('documentName', 'N/A')}")
                break
    else:
        print("Could not find items in response.")
else:
    print(r.text)
