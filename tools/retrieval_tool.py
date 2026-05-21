from langchain.tools import tool
from retriever import retriever
from langsmith import traceable

@tool
@traceable(name="semantic_retrieval")
def semantic_search(query:str)-> str:
    """
    Search vector database for semantically relevant documents.
    """
    docs = retriever.invoke(query)
    return docs
