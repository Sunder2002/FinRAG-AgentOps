from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.core.config import logger

class VectorStoreManager:
    """
    Principal Design: FAISS provides a stable, in-memory vector engine 
    that is resilient to experimental Python versions.
    """
    def __init__(self):
        logger.info("Initializing Local Embedding Model...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.store = None

    def upsert_documents(self, texts: list, metadatas: list):
        """Creates the vector index from provided text chunks."""
        try:
            self.store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            logger.info(f"SUCCESS: Indexed {len(texts)} chunks into FAISS!")
        except Exception as e:
            logger.error(f"Vector DB Error: {e}")

    def search(self, query: str) -> str:
        """Allows Agents to query the indexed financial data."""
        if not self.store:
            return "No data indexed yet."
        # Retrieve the single most relevant paragraph
        docs = self.store.similarity_search(query, k=1)
        return docs[0].page_content if docs else "No relevant data found."

vector_manager = VectorStoreManager()