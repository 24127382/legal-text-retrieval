from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.data import (
    MISSING,
    DataSchemaError,
    audit_all,
    audit_corpus,
    audit_cross_task,
    audit_legal_ir,
    load_corpus,
    load_legal_ir,
    load_legal_qa,
)
from src.data.schemas import CorpusDocument, LegalIRSample, LegalQASample


class RawDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_json(self, name: str, value: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_legal_ir_train_schema_preserves_source_text(self) -> None:
        path = self.write_json(
            "legal_ir.json",
            {"101": {"question": "  Điều 1: Áp dụng thế nào?\n", "answer": ["7", "9"]}},
        )

        samples = load_legal_ir(path)

        self.assertEqual(samples[0].sample_id, "101")
        self.assertEqual(samples[0].question, "  Điều 1: Áp dụng thế nào?\n")
        self.assertEqual(samples[0].answer, ["7", "9"])

    def test_legal_qa_train_schema(self) -> None:
        path = self.write_json(
            "legal_qa.json",
            {"201": {"question": "Căn cứ nào?", "answer": "Theo Điều 2."}},
        )

        samples = load_legal_qa(path)

        self.assertEqual(samples[0], LegalQASample("201", "Căn cứ nào?", "Theo Điều 2."))

    def test_null_answers_are_distinct_from_missing_answers(self) -> None:
        ir_path = self.write_json(
            "ir_public.json",
            {"1": {"question": "Q", "answer": None}, "2": {"question": "Q2"}},
        )
        qa_path = self.write_json(
            "qa_public.json",
            {"3": {"question": "Q", "answer": None}, "4": {"question": "Q2"}},
        )

        ir = load_legal_ir(ir_path)
        qa = load_legal_qa(qa_path)

        self.assertIsNone(ir[0].answer)
        self.assertIs(ir[1].answer, MISSING)
        self.assertIsNone(qa[0].answer)
        self.assertIs(qa[1].answer, MISSING)

    def test_corpus_missing_name_and_empty_passage_are_preserved(self) -> None:
        corpus_path = self.root / "selected-contexts"
        corpus_path.mkdir()
        (corpus_path / "context_7.json").write_text(
            json.dumps({"id": 7, "passage": "", "link": "https://example.test/7"}),
            encoding="utf-8",
        )

        documents = load_corpus(corpus_path)
        report = audit_corpus(documents)

        self.assertEqual(documents[0].passage, "")
        self.assertIs(documents[0].name, MISSING)
        self.assertEqual(report["empty_passage_count"], 1)
        self.assertEqual(report["missing_name_count"], 1)

    def test_zip_corpus_remains_supported_without_extraction(self) -> None:
        archive_path = self.root / "contexts.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(
                "selected-contexts/context_7.json",
                json.dumps({"id": 7, "passage": "A", "link": "source"}),
            )

        self.assertEqual(load_corpus(archive_path)[0].id, 7)

    def test_duplicate_ids_and_unresolved_gold_are_reported(self) -> None:
        corpus = [
            CorpusDocument(7, "A", "link-a"),
            CorpusDocument(7, "B", "link-b"),
        ]
        legal_ir = [LegalIRSample("1", "Q", ["7", "999"])]

        corpus_report = audit_corpus(corpus)
        ir_report = audit_legal_ir(legal_ir, corpus)

        self.assertEqual(
            corpus_report["duplicate_document_ids"],
            [{"document_id": 7, "count": 2}],
        )
        self.assertEqual(
            ir_report["gold"]["corpus_resolution"]["unresolved_document_ids"],
            ["999"],
        )

    def test_duplicate_top_level_sample_ids_are_not_lost(self) -> None:
        path = self.root / "duplicate_keys.json"
        path.write_text(
            '{"1":{"question":"A","answer":[]},'
            '"1":{"question":"B","answer":[]}}',
            encoding="utf-8",
        )

        samples = load_legal_ir(path)
        report = audit_legal_ir(samples)

        self.assertEqual(len(samples), 2)
        self.assertEqual(
            report["dataset"]["duplicate_sample_ids"],
            [{"sample_id": "1", "count": 2}],
        )

    def test_malformed_answer_fails_explicitly(self) -> None:
        path = self.write_json(
            "malformed_ir.json",
            {"1": {"question": "Q", "answer": "not-a-list"}},
        )

        with self.assertRaisesRegex(DataSchemaError, "expected list of strings or null"):
            load_legal_ir(path)

    def test_exact_question_overlap_cardinality(self) -> None:
        legal_ir = [
            LegalIRSample("ir-1", "one-one", []),
            LegalIRSample("ir-2", "one-many", []),
            LegalIRSample("ir-3", "many-one", []),
            LegalIRSample("ir-4", "many-one", []),
        ]
        legal_qa = [
            LegalQASample("qa-1", "one-one", "A"),
            LegalQASample("qa-2", "one-many", "A"),
            LegalQASample("qa-3", "one-many", "B"),
            LegalQASample("qa-4", "many-one", "A"),
        ]

        overlap = audit_cross_task(legal_ir, legal_qa)
        exact = overlap["exact_non_empty_question_text_overlap"]

        self.assertEqual(exact["unique_shared_question_count"], 3)
        self.assertEqual(
            exact["cardinality_counts"],
            {
                "one_to_one": 1,
                "one_to_many": 1,
                "many_to_one": 1,
                "many_to_many": 0,
            },
        )

    def test_audit_all_understands_task_directories_and_compares_corpora(self) -> None:
        for task, answer in (("LegalIR", ["7"]), ("LegalQA", "Answer")):
            task_path = self.root / task
            corpus_path = task_path / "selected-contexts"
            corpus_path.mkdir(parents=True)
            (task_path / "train.json").write_text(
                json.dumps({"1": {"question": "Question", "answer": answer}}),
                encoding="utf-8",
            )
            (corpus_path / "context_7.json").write_text(
                json.dumps({"id": 7, "passage": "Passage", "link": "source"}),
                encoding="utf-8",
            )

        report = audit_all(data_root=self.root)

        self.assertEqual(report["report_schema_version"], 2)
        self.assertTrue(report["corpora"]["comparison"]["exact_snapshot_match"])
        self.assertEqual(
            report["corpora"]["comparison"]["legal_qa_audit_reused_from"],
            "legal_ir",
        )
        self.assertEqual(report["corpora"]["legal_ir"]["document_count"], 1)
        self.assertEqual(
            report["legal_ir"]["gold"]["corpus_resolution"][
                "unresolved_unique_document_id_count"
            ],
            0,
        )

        qa_context = self.root / "LegalQA" / "selected-contexts" / "context_7.json"
        qa_context.write_text(
            json.dumps({"id": 7, "passage": "Different", "link": "source"}),
            encoding="utf-8",
        )
        different_report = audit_all(data_root=self.root)

        self.assertFalse(
            different_report["corpora"]["comparison"]["exact_snapshot_match"]
        )
        self.assertIsNone(
            different_report["corpora"]["comparison"]["legal_qa_audit_reused_from"]
        )
        self.assertEqual(
            different_report["corpora"]["legal_qa"]["passage_character_length"]["max"],
            len("Different"),
        )


if __name__ == "__main__":
    unittest.main()
