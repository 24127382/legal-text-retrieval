import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.data import (
    audit_corpus,
    audit_cross_task,
    audit_legal_ir,
    audit_legal_qa,
    load_corpus,
    load_legal_ir,
    load_legal_qa,
)


class RawDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_json(self, name: str, value) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_task_loaders_return_raw_json(self) -> None:
        ir_source = {
            "101": {"question": "  Điều 1?\n", "answer": ["7", "9"]},
            "102": {"question": "Q2"},
        }
        qa_source = {"201": {"question": "Căn cứ nào?", "answer": None}}

        legal_ir = load_legal_ir(self.write_json("ir.json", ir_source))
        legal_qa = load_legal_qa(self.write_json("qa.json", qa_source))

        self.assertEqual(legal_ir, ir_source)
        self.assertEqual(legal_qa, qa_source)
        self.assertNotIn("answer", legal_ir["102"])

    def test_corpus_loads_directory_and_zip_without_changing_text(self) -> None:
        corpus_path = self.root / "contexts"
        corpus_path.mkdir()
        document = {"id": 7, "passage": "  Passage\n", "link": "source"}
        other_document = {"id": 8, "passage": "Other", "link": "source"}
        (corpus_path / "context_7.json").write_text(
            json.dumps(document), encoding="utf-8"
        )

        archive_path = self.root / "contexts.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("context_8.json", json.dumps(other_document))
            archive.writestr("context_7.json", json.dumps(document))

        self.assertEqual(load_corpus(corpus_path), [document])
        self.assertEqual(load_corpus(archive_path), [document, other_document])

    def test_ir_and_corpus_audits_report_core_anomalies(self) -> None:
        corpus = [
            {"id": 7, "passage": "Same", "link": "a"},
            {"id": 7, "passage": "Same", "link": "b", "name": ""},
            {"id": 8, "passage": "", "link": "c", "name": "C"},
        ]
        legal_ir = {
            "1": {"question": "Q", "answer": ["7", "7", "999"]},
            "2": {"answer": []},
        }

        corpus_report = audit_corpus(corpus)
        ir_report = audit_legal_ir(legal_ir, corpus)

        self.assertEqual(
            corpus_report["duplicate_document_ids"],
            [{"document_id": 7, "count": 2}],
        )
        self.assertEqual(corpus_report["empty_passage_count"], 1)
        self.assertEqual(corpus_report["missing_name_count"], 1)
        self.assertEqual(
            corpus_report["exact_duplicate_non_empty_passage_group_count"], 1
        )
        self.assertEqual(ir_report["missing_question_count"], 1)
        self.assertEqual(ir_report["unresolved_gold_ids"], ["999"])
        self.assertEqual(
            ir_report["duplicate_gold_ids_within_samples"],
            [{"sample_id": "1", "document_ids": ["7"]}],
        )

    def test_qa_and_cross_task_audits(self) -> None:
        legal_ir = {
            "shared-id": {"question": "one-one", "answer": []},
            "ir-2": {"question": "one-many", "answer": []},
            "ir-3": {"question": "many-one", "answer": []},
            "ir-4": {"question": "many-one", "answer": []},
        }
        legal_qa = {
            "shared-id": {"question": "one-one", "answer": None},
            "qa-2": {"question": "one-many", "answer": ""},
            "qa-3": {"question": "one-many"},
            "qa-4": {"question": "many-one", "answer": "A"},
        }

        qa_report = audit_legal_qa(legal_qa)
        overlap = audit_cross_task(legal_ir, legal_qa)

        self.assertEqual(qa_report["missing_answer_count"], 1)
        self.assertEqual(qa_report["null_answer_count"], 1)
        self.assertEqual(qa_report["empty_answer_count"], 1)
        self.assertEqual(overlap["sample_id_overlap"], ["shared-id"])
        self.assertEqual(
            overlap["cardinality_counts"],
            {
                "one_to_one": 1,
                "one_to_many": 1,
                "many_to_one": 1,
                "many_to_many": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
