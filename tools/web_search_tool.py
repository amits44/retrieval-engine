from langchain.tools import tool
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from langsmith import traceable
from dotenv import load_dotenv
load_dotenv()

web_search_tool = TavilySearch(max_results=3)

@tool
@traceable(name="web_search")
def web_search(query:str)-> str:
    """
    Search the web for relevant information
    """
    result = web_search_tool.invoke({"query": query})

    if isinstance(result, dict) and "results" in result:
        results = result["results"]
    else:
        results = result

    web_docs = [
        Document(page_content=r["content"])
        for r in results
    ]

    return web_docs