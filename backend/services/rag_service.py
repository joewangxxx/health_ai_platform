
import os
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from backend.core.config import settings

class RAGService:
    def __init__(self):
        """
        Initialize RAG Service with ChromaDB and Local HuggingFace Embeddings.
        """
        # PROJECT_ROOT is f:\health_ai_platform_2.0
        # We need f:\health_ai_platform_2.0\backend\rag\vector_store
        
        # Check if PROJECT_ROOT already ends with backend (unlikely but safe)
        root = settings.PROJECT_ROOT
        if root.endswith("backend"):
            base = root
        else:
            base = os.path.join(root, "backend")
            
        self.vector_store_dir = os.path.join(base, "rag", "vector_store")
        self.embeddings = None
        self.vectorstore = None
        self._init_vectorstore()

    def _init_vectorstore(self):
        try:
            # Switch to Local HuggingFace Embeddings
            # No API Key required
            self.embeddings = HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese"
            )
            
            if os.path.exists(self.vector_store_dir) and os.listdir(self.vector_store_dir):
                self.vectorstore = Chroma(
                    persist_directory=self.vector_store_dir,
                    embedding_function=self.embeddings
                )
                print(f"✅ RAGService: Vector Store loaded from {self.vector_store_dir}")
            else:
                print(f"⚠️ RAGService: Vector Store empty or not found at {self.vector_store_dir}")
                
        except Exception as e:
            print(f"❌ RAGService Initialization Error: {e}")

    def search_context(self, query: str, k: int = 3) -> str:
        """
        Search for relevant context in the Knowledge Base.
        Returns combined text of top-k documents.
        """
        if not self.vectorstore:
            return ""

        try:
            # Similarity Search
            docs = self.vectorstore.similarity_search(query, k=k)
            
            if not docs:
                return ""
            
            # Combine content
            context_parts = []
            for i, doc in enumerate(docs):
                source = os.path.basename(doc.metadata.get("source", "Unknown"))
                context_parts.append(f"[Ref {i+1} - {source}]: {doc.page_content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            print(f"❌ RAG Search Error: {e}")
            return ""

# Singleton Instance
rag_service = RAGService()
