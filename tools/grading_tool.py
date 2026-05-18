from langchain_tools import tool

@tool
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
def verify_grounding(documents:str, generation:str)-> str:
    """
    verify if the generation is grounded in the provided documents.
    """
    result = hallucination_grader.invoke({
        "documents": documents,
        "generation": generation
    })
    return result.binary_score