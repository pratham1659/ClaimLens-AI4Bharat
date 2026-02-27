import os
from langchain_community.vectorstores import FAISS


def build_or_load_vectorstore(
    clause_documents,
    embedding_model,
    index_path: str
):
    """
    Builds FAISS vector store if it does not exist.
    Otherwise loads the existing index.

    Parameters:
        clause_documents: List[Document]
        embedding_model: HuggingFaceEmbeddings instance
        index_path: Folder path where FAISS index is stored

    Returns:
        FAISS vectorstore object
    """

    if os.path.exists(index_path):
        print("Loading existing FAISS index...")
        vectorstore = FAISS.load_local(
            index_path,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
    else:
        print("Building FAISS index from clause documents...")
        vectorstore = FAISS.from_documents(
            clause_documents,
            embedding_model
        )
        vectorstore.save_local(index_path)
        print("FAISS index built and saved.")

    return vectorstore