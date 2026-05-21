from state import GraphState
#from chains import relevance_grader, hallucination_grader, answer_grader
from retriever import retriever
from langsmith import traceable
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, trim_messages
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from tools.retrieval_tool import semantic_search
from tools.web_search_tool import web_search
from tools.grading_tool import grade_document_relevance, verify_grounding, verify_answer_quality
from dotenv import load_dotenv
load_dotenv()

#---------LLM------------

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

#---------RAG generation chain-----------

rag_prompt = ChatPromptTemplate.from_messages([
    ("system",
    "You are an expert research assistant. Provide comprehensive, well-cited answers based on the context below.\n\n"
    "Context: {context}\n\n"
    "When answering:\n"
    "- Synthesize information from multiple sources when available\n"
    "- Highlight key findings and main arguments\n"
    "- Note any conflicting information or gaps in the sources\n"
    "- Be precise and academic in tone\n\n"),
   MessagesPlaceholder(variable_name="messages"),
])
rag_chain = rag_prompt | llm | StrOutputParser()

#---------Retrieve Node---------

def retrieve_node(state: GraphState):
    question= state["messages"][-1].content
    docs = semantic_search.invoke(question)
    return {"documents": docs}

#------------Grade Document Node-----------

def grade_documents_node(state: GraphState):
    question= state["messages"][-1].content
    filtered_docs =[]
    needs_web_search =False
    for doc in state["documents"]:
        score = grade_document_relevance.invoke({"question": question, "document": doc.page_content})
        if score == "yes":
            filtered_docs.append(doc)
        else:
            needs_web_search = True
    if len(filtered_docs) == 0:
        needs_web_search = True
    return {
        "documents": filtered_docs,
        "web_fallback": needs_web_search
    }


#------------Web Search Node-----------

def web_search_node(state:GraphState):
    question= state["messages"][-1].content
    web_docs = web_search.invoke(question)
    
    combined_docs = state["documents"]+ web_docs
    return {"documents": combined_docs}

#------------Generation Node-----------

def generate_node(state:GraphState):
    context = "\n\n".join([doc.page_content for doc in state["documents"]])
    trimmed_history = trim_messages(
        state["messages"],
        max_tokens=5,       
        token_counter=len,
        strategy="last"    
    )
    generation = rag_chain.invoke({"context": context, "messages": trimmed_history})
    return {
        "generation": generation,
        "messages":[AIMessage(content=generation)]
    }

#------------Hallucination Check Node-----------

def hallucination_check_node(state: GraphState):
    question = state["messages"][-1].content
    docs_text ="\n\n".join([doc.page_content for doc in state["documents"]])

    grounding_score = verify_grounding.invoke({
        "documents": docs_text,
        "generation": state["generation"]
    })
    answer_score = verify_answer_quality.invoke({
        "question": question,
        "generation": state["generation"]
    })
    hallucination_detected = not(
        grounding_score == "yes"
        and answer_score == "yes"
    )
    return{"hallucination": hallucination_detected}
