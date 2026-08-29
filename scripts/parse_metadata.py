from src.preprocess.parser import process_cleaned_csv

INPUT_CSV = "cleaned_data.csv"
OUTPUT_JSONL = "output/document_metadata.jsonl"


def main():
    process_cleaned_csv(
        input_csv=INPUT_CSV,
        output_jsonl=OUTPUT_JSONL,
    )


if __name__ == "__main__":
    main()