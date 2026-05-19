from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

class RelevanceGrade(BaseModel):
    binary_score: str = Field(description="'yes' if releant otherwise 'no'")

relevance_grader = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a research document relevance grader. Evaluate if a document contains information "
     "relevant to answering the research question. Consider:\n"
     "- Direct answers to the question\n"
     "- Supporting evidence or context\n"
     "- Related findings or data\n"
     "Output 'yes' if relevant, 'no' if not."),
    ("human", "Research Question: {question}\n\nDocument Excerpt: {document}"),
])| llm.with_structured_output(RelevanceGrade) 

class HallucinationGrade(BaseModel):
    binary_score: str = Field(description="'yes' if grounded, 'no' if hallucinating")

hallucination_grader = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a fact-checker for research outputs. Verify that the generated answer is "
     "fully grounded in the provided documents. If the answer makes claims not supported "
     "by the documents, output 'no'. If all claims are supported, output 'yes'."),
    ("human", "Source Documents: {documents}\n\nGenerated Answer: {generation}"),
]) | llm.with_structured_output(HallucinationGrade)

class AnswerGrade(BaseModel):
    binary_score: str = Field(description= "'yes' if the answer directly resolves the research question, 'no',if it does not resolves the user question ")

answer_grader = ChatPromptTemplate.from_messages([
        ("system", 
     "Evaluate if this answer adequately addresses the research question. "
     "An adequate answer should be comprehensive, specific, and directly relevant. "
     "Output 'yes' or 'no'."),
    ("human", "Research Question: {question}\n\nGenerated Answer: {generation}"),
]) | llm.with_structured_output(AnswerGrade)