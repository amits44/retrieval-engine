from langchain.tools import tool

@tool
def retrieve_memory(query: str) -> str:
    """
    Retrieve relevant past conversation memory.
    """