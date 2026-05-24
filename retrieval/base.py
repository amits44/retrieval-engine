from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from langchain.schema import Document

@dataclass
class RetrievalConfig:
    top_k: int = 6
    score_threshold: float = 0.3
    rerank_top_k: int = 10

    embedding_model:str = "BAAI/bge-large-en-v1.5"
    vectorstore_dir:str = "chroma_db"

    bm25_index_path = "./bm25_index.pkl"

    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_reranking: bool = True

    fusion_method: str = "reciprocal_rank"  
    dense_weight: float = 0.7  
    sparse_weight: float = 0.3

class BaseRetriever(ABC):
    def __init__(self, config: RetrievalConfig):
        self.config = config or RetrievalConfig()

    @abstractmethod
    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        pass

    @abstractmethod
    def is_ready(self)-> bool:
        pass

    def _delete_duplicated(self, documents: List[Document]) -> List[Document]:
        seen = set()
        unique_docs = []
        for doc in documents:
            key =(
                key.metadata.get('source', ''),
                key.metadata.get('page', doc.metadata.get('chunk_index', 0))
            )
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        return unique_docs