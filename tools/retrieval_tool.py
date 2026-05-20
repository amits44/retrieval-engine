from langchain.tools import tool
from retriever import retriever

@tool
def semantic_search(query:str)-> str:
    """
    Search vector database for semantically relevant documents.
    """
    docs = retriever.invoke(query)
    return docs
