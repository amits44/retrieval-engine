from langchain.tools import tool
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

web_search_tool = TavilySearch(max_results=3)

@tool
def web_search(query:str)-> str:
    """
    Search the web for relevant information
    """
    result = web_search_tool.invoke({"query": query})
    if isinstance(results, dict) and "results" in results:
        results = results["results"]
    else:
        results = search_output

    web_docs = [
        Document(page_content=r["content"])
        for r in results
    ]

    return web_docs