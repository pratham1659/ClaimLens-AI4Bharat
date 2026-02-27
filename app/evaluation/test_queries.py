"""
Ground truth queries for retrieval evaluation.
Each query contains the clause_number that should be retrieved.
"""

TEST_QUERIES = [
    {
        "query": "What is the waiting period for cataract treatment?",
        "relevant_clause_numbers": ["2."],  # Code-Excl02
    },
    {
        "query": "What is the waiting period for pre-existing diseases?",
        "relevant_clause_numbers": ["7.1.1."],  # Pre-existing Diseases
    },
    {
        "query": "What is the moratorium period?",
        "relevant_clause_numbers": ["12.", "8.1.10."],  # Moratorium clauses
    },
]