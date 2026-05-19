from langgraph.graph import StateGraph, END
from state import GraphState
from nodes import (
    retrieve_node,
    grade_documents_node,
    web_search_node,
    generate_node,
    hallucination_check_node)
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

#---------------sqlite checkpointer--------------

conn = sqlite3.connect("chat_history.db", check_same_thread=False)
saver = SqliteSaver(conn)

#--------------routing function---------------------

def route_after_grading(state:GraphState):
    if state['web_fallback']:
        return "web_search"
    return "generate"

def route_after_hallucination_check(state:GraphState):
    retry_count = state.get("retry_count", 0)
    if state["hallucination"] and retry_count < 3:
        return "generate"
    return END

#----------------Graph---------------------

workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)
workflow.add_node("hallucination_check", hallucination_check_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges("grade_documents", route_after_grading)
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", "hallucination_check")
workflow.add_conditional_edges("hallucination_check", route_after_hallucination_check)

app = workflow.compile(checkpointer = saver)

def retrieve_thread():
    all_threads = set()
    for checkpoint in saver.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)