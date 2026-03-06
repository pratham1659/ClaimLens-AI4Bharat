
# Backend Quick Notes

## Titan Embedding Dependencies

Install required packages:

```bash
pip install boto3 faiss-cpu numpy
```

## Titan + FAISS Example

Run the sample script:

```bash
cd backend
python scripts/titan_faiss_example.py
```

The script embeds 5 sample clauses with `amazon.titan-embed-text-v1`, builds a FAISS index, and runs a similarity search.
