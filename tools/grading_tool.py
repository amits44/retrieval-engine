from langchain.tools import tool
from chains import relevance_grader, hallucination_grader, answer_grader
from langsmith import traceable

@tool
@traceable(name="grading_tool")
def grade_document_relevance(question:str, document:str)-> str:
    """
    Grade the relevance of the document to the question.
    """
    result = relevance_grader.invoke({
        "question": question,
        "document": document
    })
    return result.binary_score

@tool
@traceable(name="verify_grounding_tool")
def verify_grounding(documents:str, generation:str)-> str:
    """
    verify if the generation is grounded in the provided documents.
    """
    result = hallucination_grader.invoke({
        "documents": documents,
        "generation": generation
    })
    return result.binary_score

@tool
@traceable(name="verify_answer_quality_tool")
def verify_answer_quality(question:str, generation:str)-> str:
    """
    Evaluate if the generated answer adequately addresses the research question.
    """
    result = answer_grader.invoke({
        "question": question,
        "generation": generation
    })
    return result.binary_score