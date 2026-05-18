from langchain_tools import tol
from tavily_search import TavilySearch

web_search_tool = TavilySearch(max_results=3)

@tool
def web_search(query:str)-> str:
    """
    Search the web for relevant information
    """
    result = web_search_tool.invoke({"query": query})
    return str(result)