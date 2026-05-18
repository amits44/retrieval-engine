from tools.retrieval_tool import semantic_search
from tools.web_search_tool import web_search    
from tools.grading_tool import grade_document_relevance, verify_grounding

TOOLS =[
    semantic_search,
    web_search,
    grade_document_relevance,
    verify_grounding
]