import pandas as pd
from src.preprocess.cleaner import preprocess_single_document
from src.preprocess.loader import load_documents_from_dir

DATA_DIR = "/kaggle/input/datasets/akiyavyre/legal-text/selected-contexts"
OUTPUT_CSV_PATH = "cleaned_data.csv"


def main():
    print("Loading documents...")
    documents = load_documents_from_dir(DATA_DIR)
    print(f"Loaded documents: {len(documents):,}")

    cleaned_documents = []
    for doc in documents:
        cleaned_passage = preprocess_single_document(doc)
        if cleaned_passage:
            cleaned_documents.append({
                "document_id": doc.get("id", ""),
                "cleaned_text": cleaned_passage,
                "document_title": doc.get("name", ""),
                "link": doc.get("link", ""),
            })

    print(f"Cleaned documents: {len(cleaned_documents):,}")

    cleaned_df = pd.DataFrame(cleaned_documents)
    cleaned_df.to_csv(
        OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig"
    )
    print(f"✔ Đã lưu thành công file: {OUTPUT_CSV_PATH}")


if __name__ == "__main__":
    main()