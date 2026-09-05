import numpy as np

def calculate_recall_at_k(retrieved_docs, ground_truth, k=10):
    """
    Calculate Recall@K.
    
    Args:
        retrieved_docs (list): List of retrieved document IDs, ordered by relevance.
        ground_truth (list): List of actual relevant document IDs.
        k (int): Number of top retrieved documents to consider.
        
    Returns:
        float: Recall@K score.
    """
    if not ground_truth:
        return 0.0
        
    top_k_retrieved = retrieved_docs[:k]
    relevant_retrieved = set(top_k_retrieved).intersection(set(ground_truth))
    
    recall = len(relevant_retrieved) / len(ground_truth)
    return recall

def calculate_mrr(retrieved_docs, ground_truth):
    """
    Calculate Mean Reciprocal Rank (MRR).
    
    Args:
        retrieved_docs (list): List of retrieved document IDs.
        ground_truth (list): List of actual relevant document IDs.
        
    Returns:
        float: MRR score.
    """
    for i, doc_id in enumerate(retrieved_docs):
        if doc_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0
