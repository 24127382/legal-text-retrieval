import unittest

from src.ir import build_bm25, evaluate_retrieval, retrieve_bm25


class BM25SanityTests(unittest.TestCase):
    def test_retrieval_is_ranked_and_deduplicates_documents(self) -> None:
        chunks = [
            {"chunk_id": "a:0", "document_id": "a", "text": "thuế thuế đất"},
            {"chunk_id": "a:1", "document_id": "a", "text": "thuế"},
            {"chunk_id": "b:0", "document_id": "b", "text": "hôn nhân"},
        ]
        samples = {"q": {"question": "thuế đất", "answer": ["a"]}}

        index = build_bm25(chunks)
        run = retrieve_bm25(index, samples, top_k_chunks=3, top_k_documents=3)

        self.assertEqual(run["rankings"]["q"][0], "a")
        self.assertEqual(len(run["rankings"]["q"]), 2)
        self.assertEqual(len(set(run["rankings"]["q"])), 2)

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
