import unittest

from src.ir import (
    aggregate_documents,
    build_bm25,
    evaluate_retrieval,
    make_legalir_split,
    retrieve_bm25,
)


class BM25SanityTests(unittest.TestCase):
    def test_document_aggregation_uses_one_candidate_universe(self) -> None:
        chunk_hits = [
            {
                "chunk_id": "a:0",
                "document_id": "a",
                "score": 5.0,
                "chunk_rank": 1,
            },
            {
                "chunk_id": "b:0",
                "document_id": "b",
                "score": 4.0,
                "chunk_rank": 2,
            },
            {
                "chunk_id": "b:1",
                "document_id": "b",
                "score": 4.0,
                "chunk_rank": 3,
            },
            {
                "chunk_id": "a:1",
                "document_id": "a",
                "score": 1.0,
                "chunk_rank": 4,
            },
            {
                "chunk_id": "c:0",
                "document_id": "c",
                "score": 4.0,
                "chunk_rank": 5,
            },
        ]

        rankings = {
            method: aggregate_documents(chunk_hits, method=method)
            for method in ("max", "mean_top_2", "mean_top_3", "sum_top_2")
        }
        document_ids = {
            method: [document["document_id"] for document in ranking]
            for method, ranking in rankings.items()
        }

        self.assertEqual(document_ids["max"][:2], ["a", "b"])
        self.assertEqual(document_ids["mean_top_2"][:2], ["b", "c"])
        self.assertEqual(document_ids["mean_top_3"][:2], ["b", "c"])
        self.assertEqual(document_ids["sum_top_2"][:2], ["b", "a"])
        self.assertEqual(document_ids["mean_top_2"][1:], ["c", "a"])
        self.assertEqual(
            {method: set(ids) for method, ids in document_ids.items()},
            {method: {"a", "b", "c"} for method in document_ids},
        )
        self.assertTrue(all(len(ids) == len(set(ids)) for ids in document_ids.values()))

    def test_split_groups_exact_questions_and_assigns_every_id_once(self) -> None:
        samples = {
            "a": {"question": "same"},
            "b": {"question": "same"},
            "c": {"question": "different"},
            "d": {"question": None},
        }

        split_ids = make_legalir_split(samples)
        assignment = {
            sample_id: split_name
            for split_name, ids in split_ids.items()
            for sample_id in ids
        }

        self.assertEqual(assignment["a"], assignment["b"])
        self.assertEqual(set(assignment), set(samples))
        self.assertEqual(sum(map(len, split_ids.values())), len(samples))

    def test_retrieval_is_ranked_and_deduplicates_documents(self) -> None:
        chunks = [
            {"chunk_id": "a:0", "document_id": "a", "text": "thuế thuế đất"},
            {"chunk_id": "a:1", "document_id": "a", "text": "thuế"},
            {"chunk_id": "b:0", "document_id": "b", "text": "hôn nhân"},
        ]
        samples = {"q": {"question": "thuế đất", "answer": ["a"]}}

        index = build_bm25(chunks)
        run = retrieve_bm25(
            index,
            samples,
            top_k_chunks=3,
            top_k_documents=3,
            candidate_depths=(1, 2, 3),
        )

        self.assertEqual(run["rankings"]["q"][0], "a")
        self.assertEqual(len(run["rankings"]["q"]), 2)
        self.assertEqual(len(set(run["rankings"]["q"])), 2)
        self.assertEqual(
            run["unique_documents_from_chunk_pool"]["queries_below_depth"],
            {1: 0, 2: 0, 3: 1},
        )

    def test_metrics_match_tiny_document_ranking(self) -> None:
        samples = {
            "q1": {"question": "one", "answer": ["a", "b"]},
            "q2": {"question": "two", "answer": ["z"]},
        }
        rankings = {
            "q1": ["x", "a", "y", "b", "w"],
            "q2": ["a", "b", "c", "d", "z"],
        }

        metrics = evaluate_retrieval(samples, rankings, candidate_depths=(1, 2, 5))

        self.assertEqual(metrics["candidate_recall"][1]["mean"], 0.0)
        self.assertEqual(metrics["candidate_recall"][2]["mean"], 0.25)
        self.assertEqual(metrics["candidate_recall"][5]["mean"], 1.0)
        self.assertAlmostEqual(metrics["mrr"], (1 / 2 + 1 / 5) / 2)
        self.assertAlmostEqual(metrics["official_style_top_5"]["precision"], 0.3)
        self.assertEqual(metrics["official_style_top_5"]["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
