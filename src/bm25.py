from rank_bm25 import BM25Okapi


class BM25:
    """Build a BM25Okapi index from chunk texts."""

    @staticmethod
    def create_index(chunks):
        tokenized_chunks = [chunk.split() for chunk in chunks]
        return BM25Okapi(tokenized_chunks)