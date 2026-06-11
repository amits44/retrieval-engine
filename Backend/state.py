from typing import TypedDict, List, Optional, Annotated
from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage],add_messages]
    question: str
    generation: str
    web_fallback: bool
    hallucination: bool
    retry_count: int
    documents: List[Document]
    sources_used: Optional[List[str]]
    search_type: Optional[str]