from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from src.core.config import logger

class VectorStoreManager:
    """
    Enterprise Vector DB Manager using Qdrant.
    Handles persistent, distributed vector storage.
    """
    def __init__(self):
        # The model is now cached via Docker volumes!
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.collection_name = "financial_audits"
        
        try:
            # Connect to the Qdrant container running on the Docker network
            self.client = QdrantClient(url="http://qdrant:6333")
            
            # Create the collection if it doesn't exist (384 is the dimension size for MiniLM)
            if not self.client.collection_exists(collection_name=self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info(f"Created new Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Connected to existing Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {str(e)}")
            self.client = None

    def upsert_documents(self, texts: list, metadatas: list):
        if not self.client:
            logger.error("Cannot upsert: Qdrant client is not initialized.")
            return

        try:
            # Convert text chunks to math (vectors)
            logger.info("Generating embeddings for document chunks...")
            vectors = self.embeddings.embed_documents(texts)
            
            # Format payloads for Qdrant
            points = []
            for i, (vector, text, metadata) in enumerate(zip(vectors, texts, metadatas)):
                payload = {**metadata, "page_content": text}
                points.append(
                    PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
                )
            
            # Upload to DB
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"✅ SUCCESS: Indexed {len(points)} chunks into Qdrant!")
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert documents to Qdrant: {str(e)}")

    def search(self, query: str, limit: int = 1) -> str:
        if not self.client:
            return "No database connection."

        try:
            # Convert search query to vector
            query_vector = self.embeddings.embed_query(query)
            
            # Search Qdrant
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            if not search_result:
                return "No results found in database."
                
            # Return the text content of the best match
            return search_result[0].payload.get("page_content", "No content found.")
            
        except Exception as e:
            logger.error(f"❌ Search failed: {str(e)}")
            return "Search failed due to database error."

vector_manager = VectorStoreManager()