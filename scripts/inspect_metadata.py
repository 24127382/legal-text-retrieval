import json
import random

JSONL_PATH = "output/document_metadata.jsonl"


def inspect_metadata(file_path: str):
    total_docs = 0
    empty_unit_docs = 0
    level_counts = {}

    docs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            docs.append(doc)
            total_docs += 1

            units = doc.get("units", [])
            if not units:
                empty_unit_docs += 1

            for unit in units:
                lvl = unit["level"]
                level_counts[lvl] = level_counts.get(lvl, 0) + 1

    print("=" * 60)
    print("1. THỐNG KÊ TỔNG QUAN PARSER")
    print("=" * 60)
    print(f"Tổng số văn bản                 : {total_docs:,}")
    print(
        f"Số văn bản KHÔNG bắt được Unit nào : {empty_unit_docs:,} ({empty_unit_docs/total_docs*100:.2f}%)"
    )
    print("\nSố lượng Unit phát hiện theo cấp độ:")
    for lvl, count in sorted(
        level_counts.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {lvl:<15}: {count:,}")

    # -------------------------------------------------------------
    # 2. SOI CHI TIẾT 1 VĂN BẢN MẪU
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("2. KIỂM TRA MẪU THỰC TẾ (SAMPLE CHECK)")
    print("=" * 60)

    valid_docs = [
        d
        for d in docs
        if any(u["level"] == "article" for u in d["units"])
    ]
    if not valid_docs:
        print("Không tìm thấy doc nào có article!")
        return

    sample_doc = random.choice(valid_docs)
    full_text = sample_doc["text"]

    print(f"Document ID   : {sample_doc['document_id']}")
    print(f"Fingerprint   : {sample_doc['fingerprint']}")
    print(f"Tổng số units : {len(sample_doc['units'])}")
    print("-" * 60)

    article_units = [
        u for u in sample_doc["units"] if u["level"] == "article"
    ][:3]
    for idx, unit in enumerate(article_units):
        sliced_text = full_text[unit["char_start"] : unit["char_end"]]
        print(
            f"\n---> [ARTICLE UNIT {idx+1}] Level: {unit['level']} | Số: {unit['number']} | Title: {unit['title']}"
        )
        print(
            f"Range: {unit['char_start']} -> {unit['char_end']} (Độ dài: {len(sliced_text)} chars)"
        )
        print("Trích đoạn nội dung (150 ký tự đầu):")
        print("---")
        print(sliced_text[:150].strip() + "...")
        print("---")


if __name__ == "__main__":
    inspect_metadata(JSONL_PATH)