from state import GraphState
from chains import relevance_grader, hallucination_grader, AnswerGrader
from retriever import retriever
#from langchain_community.tools.tavily_search import TavilySearchResults
from langsmith import traceable
from langchain_tavily import TavilySearch
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, trim_messages
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

web_search_tool = TavilySearch(max_results=3)
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

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

@traceable(name="vector store retrieval")
def retrieve(state: GraphState) -> GraphState:
    current_question= state["messages"][-1].content
    docs = retriever.invoke(current_question)
    return {"documents": docs}

def graded_documents(state: GraphState) -> GraphState:
    filtered, needs_web =[], False
    for doc in state["documents"]:
        score = relevance_grader.invoke({"question": state["messages"][-1].content, "document": doc.page_content})
        if score.binary_score == "yes":
            filtered.append(doc)
        else:
            needs_web = True
    return {"documents": filtered, "web_fallback": needs_web or len(filtered) == 0}

def web_search(state:GraphState) -> GraphState:
    search_output = web_search_tool.invoke({"query": state["messages"][-1].content})
    
    if isinstance(search_output, dict) and "results" in search_output:
        results_list = search_output["results"]
    else:
        results_list = search_output
    web_docs = [Document(page_content=r["content"]) for r in results_list]
    return {"documents": state["documents"] + web_docs}

def generate(state:GraphState)-> GraphState:
    context = "\n\n".join([doc.page_content for doc in state["documents"]])
    trimmed_history = trim_messages(
        state["messages"],
        max_tokens=5,       
        token_counter=len,
        strategy="last"    
    )
    generation = rag_chain.invoke({"context": context, "messages": trimmed_history})
    return {"generation": generation,"messages":[AIMessage(content=generation)]}

def check_hallucination(state: GraphState) -> GraphState:
    docs_text ="\n\n".join([doc.page_content for doc in state["documents"]])
    h_score = hallucination_grader.invoke({"documents": docs_text, "generation": state["generation"]})
    a_score = AnswerGrader.invoke({"question": state["messages"][-1].content, "generation": state["generation"]})
    is_good = h_score.binary_score == "yes" and a_score.binary_score == "yes"
    return{"hallucination": not is_good}
