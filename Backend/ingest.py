import os
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    DirectoryLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader ,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def load_documents(docs_dir: str= DOCS_DIR):
    documents=[]
    loaders=[
        DirectoryLoader(docs_dir, glob="**/*.pdf", loader_cls = PyPDFLoader),
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls = TextLoader),
        DirectoryLoader(docs_dir, glob="**/*.md", loader_cls = UnstructuredMarkdownLoader),
        DirectoryLoader(docs_dir, glob="**/*.csv", loader_cls = CSVLoader ),
        DirectoryLoader(docs_dir, glob="**/*.docs", loader_cls = UnstructuredWordDocumentLoader)
    ]
    for loader in loaders:
        try:
            docs = loader.load()
            documents.extend(docs)
            print(f"  Loaded {len(docs)} docs with {loader.__class__.__name__}")
        except Exception as e:
            print(f"  Warning: {e}")

    if not documents:
        raise ValueError(f"No documents found in '{docs_dir}/'. Add some .pdf, .txt, or .md files.")

    print(f"\nTotal documents loaded: {len(documents)}")
    return documents

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"split into {len(chunks)} chunks"
        f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    return chunks

def build_vectorstore(chunks, persist_dir: str= CHROMA_DIR):
    print("\nEmbedding chunks with huggingface text-embedding-3-small ...")
    embedding = HuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

    vectorstore= Chroma.from_documents(
        documents= chunks,
        embedding = embedding,
        persist_directory = persist_dir,
    )
    print("vector store saved to '{persist_dir}/'")
    return vectorstore

if __name__ == "__main__":
    print("=== CRAG Tech Support — Ingestion Pipeline ===\n")

    if not Path(DOCS_DIR).exists():
        os.makedirs(DOCS_DIR)
        print(f"Created '{DOCS_DIR}/' — add your PDFs, TXTs, or MDs there and re-run.")
    else:
        docs   = load_documents(DOCS_DIR)
        chunks = split_documents(docs)
        build_vectorstore(chunks, CHROMA_DIR)
        print("\nIngestion complete. Run app.py to start the chatbot.")
    
    
