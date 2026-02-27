import os
from langchain_community.vectorstores import FAISS


def build_or_load_vectorstore(
    clause_documents,
    embedding_model,
    index_path: str
):
    """
    Builds a FAISS vector store from clause documents if one does not exist.
    Loads the existing index if it does.

    Parameters:
        clause_documents (List[Document]): Chunked policy clause documents.
        embedding_model (HuggingFaceEmbeddings): Encoder for dense vectors.
        index_path (str): Folder path where the FAISS index is saved/loaded.

    Returns:
        FAISS: A LangChain FAISS vectorstore ready for similarity search.
    """

    if os.path.exists(index_path):
        print(f"Loading existing FAISS index from: {index_path}")

        vectorstore = FAISS.load_local(
            index_path,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
        print("FAISS index loaded successfully.")

    else:
        print(f"No existing index found. Building FAISS index from {len(clause_documents)} clauses...")
        vectorstore = FAISS.from_documents(
            clause_documents,
            embedding_model
        )
        vectorstore.save_local(index_path)
        print(f"FAISS index built and saved to: {index_path}")

    return vectorstore