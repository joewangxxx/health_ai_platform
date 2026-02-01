
import os
import shutil
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from backend.core.config import settings

# --- Configuration ---
# Allow running from project root or checks
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")

def build_knowledge_base():
    """
    Builds the RAG Knowledge Base:
    1. Loads PDFs from backend/rag/docs/
    2. Splits text into chunks
    3. Generates embeddings using Local HuggingFace Model (text2vec-base-chinese)
    4. Stores vectors in ChromaDB (backend/rag/vector_store/)
    """
    print(f"🚀 Starting Knowledge Base Build Process...")
    print(f"📂 Docs Dir: {DOCS_DIR}")
    print(f"💾 Vector Store Dir: {VECTOR_STORE_DIR}")

    # 1. Check Docs
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print("⚠️ Docs directory created. Please put PDF files in backend/rag/docs/")
        return

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print("⚠️ No PDF files found in backend/rag/docs/. Skipping build.")
        return

    documents = []
    print(f"📄 Found {len(pdf_files)} PDF(s). Loading...")
    
    for pdf_file in pdf_files:
        file_path = os.path.join(DOCS_DIR, pdf_file)
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            documents.extend(docs)
            print(f"  ✅ Loaded: {pdf_file} ({len(docs)} pages)")
        except Exception as e:
            print(f"  ❌ Failed to load {pdf_file}: {e}")

    if not documents:
        print("❌ No documents loaded.")
        return

    # 2. Split Text
    print("✂️ Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    splits = text_splitter.split_documents(documents)
    print(f"  -> Generated {len(splits)} chunks.")

    # 3. Initialize Embeddings (Local HuggingFace)
    print("🧠 Initializing Embeddings Model (shibing624/text2vec-base-chinese)...")
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
    except Exception as e:
        print(f"❌ Failed to load HuggingFace model: {e}")
        return
    
    # 4. Create/Update Vector Store
    print("💾 Creating Chroma Vector Store...")

    # 4. Create/Update Vector Store
    print("💾 Creating Chroma Vector Store...")
    
    # Clear existing if needed? For now, we persist/append or overwrite?
    # Chroma persists automatically if directory is provided.
    
    try:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=VECTOR_STORE_DIR
        )
        # vectorstore.persist() # In newer langchain/chroma, it persists automatically on write usually
        print(f"✅ Knowledge Base Built Successfully! Saved to {VECTOR_STORE_DIR}")
        print(f"📊 Total Vectors: {vectorstore._collection.count()}")
        
    except Exception as e:
        print(f"❌ Failed to create vector store: {e}")
        print("💡 Hint: Ensure the Embedding Model is supported by your API provider.")

if __name__ == "__main__":
    build_knowledge_base()
