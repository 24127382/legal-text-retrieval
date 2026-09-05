import json
import os

def check_duplicates(file_path):
    ids = set()
    dups = 0
    total = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                item_id = item.get('id')
                if item_id:
                    if item_id in ids:
                        dups += 1
                    else:
                        ids.add(item_id)
                total += 1
            except Exception as e:
                pass
                
    print(f"Total lines/items processed: {total}")
    print(f"Total duplicate items found: {dups}")
    print(f"Total unique items: {len(ids)}")

if __name__ == "__main__":
    check_duplicates("vbpl_metadata_raw.jsonl")
