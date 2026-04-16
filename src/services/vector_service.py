from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import os
from src.core.config import logger

class VectorStoreManager:
    def __init__(self):
        self.collection_name = "financial_audits"
        self.embeddings = None
        self.client = None

    def _initialize(self):
        """ELITE FIX: Lazy Initialization. Only connects when actively called, bypassing boot-time race conditions."""
        if self.client is None:
            try:
                logger.info("Initializing HuggingFace Embeddings...")
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                
                qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
                qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
                
                logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}...")
                self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
                
                if not self.client.collection_exists(collection_name=self.collection_name):
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                    )
                    logger.info("✅ Qdrant Collection created.")
            except Exception as e:
                logger.error(f"❌ Qdrant Initialization Failed: {str(e)}")
                self.client = None

    def upsert_documents(self, texts: list, metadatas: list):
        self._initialize()
        if not self.client or not texts: 
            return False
        
        try:
            vectors = self.embeddings.embed_documents(texts)
            points = [
                PointStruct(id=str(uuid.uuid4()), vector=v, payload={**m, "page_content": t})
                for v, t, m in zip(vectors, texts, metadatas)
            ]
            self.client.upsert(collection_name=self.collection_name, points=points)
            return True
        except Exception as e:
            logger.error(f"❌ Upsert failed: {str(e)}")
            return False

    def search(self, query: str, limit: int = 2) -> str:
        self._initialize()
        if not self.client: 
            return "Database connection offline. Proceeding without vector context."
        
        try:
            query_vector = self.embeddings.embed_query(query)
            results = self.client.search(
                collection_name=self.collection_name, 
                query_vector=query_vector, 
                limit=limit
            )
            if not results: 
                return "No relevant data found in vector search."
                
            return "\n\n".join([res.payload.get("page_content", "") for res in results])
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return f"Database error during search: {str(e)}"

vector_manager = VectorStoreManager()