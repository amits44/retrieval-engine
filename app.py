
import streamlit as st
from graph import app
from langsmith import Client
from dotenv import load_dotenv
import os
from pathlib import Path
from langchain_core.messages import HumanMessage
import uuid

load_dotenv()

ls_client = Client()

# initializing session state

if "run_id" not in st.session_state:
    st.session_state.run_id = None

if "chat_threads" not in st.session_state:
    st.session_state['chat_threads'] = {} 

if "thread_titles" not in st.session_state:  
    st.session_state['thread_titles'] = {}

if "thread_id" not in st.session_state:
    st.session_state['thread_id'] = str(uuid.uuid4())
    st.session_state['chat_threads'][st.session_state['thread_id']] = []
    st.session_state['thread_titles'][st.session_state['thread_id']] = "New Chat"


# helper function

def reset_chat():
    new_thread_id = str(uuid.uuid4())
    st.session_state['thread_id'] = new_thread_id
    st.session_state['chat_threads'][new_thread_id] = []
    st.session_state['thread_titles'][new_thread_id] = "New Chat"

#  sidebar for thread management and document upload

st.sidebar.title("Chat History")
if st.sidebar.button('➕ New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')
# Display buttons for previous threads
for t_id in st.session_state['chat_threads'].keys():
    chat_title = st.session_state['thread_titles'].get(t_id, "Saved Chat")
    
    if st.sidebar.button(chat_title, key=f"btn_{t_id}"):
        st.session_state['thread_id'] = t_id

st.sidebar.markdown("---")
st.sidebar.header("Document Management")

# Define the uploader BEFORE checking it
uploaded_files = st.sidebar.file_uploader(
    "Upload research documents",
    type=['pdf', 'txt', 'md'],
    accept_multiple_files=True
)

if uploaded_files:
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    for uploaded_file in uploaded_files:
        file_path = docs_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    st.sidebar.success(f"{len(uploaded_files)} file(s) uploaded to docs/")
    st.sidebar.info("Run ingestion to index new documents")

if st.sidebar.button("Index Documents"):
    with st.spinner("Indexing documents..."):
        from ingest import load_documents, split_documents, build_vectorstore, DOCS_DIR, CHROMA_DIR
        try:
            docs = load_documents(DOCS_DIR)
            chunks = split_documents(docs)
            build_vectorstore(chunks, CHROMA_DIR)
            st.sidebar.success("Documents indexed successfully!")
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")

# chat interface

st.title("C-RAG Research Assistant")
st.markdown("*Corrective RAG with web fallback for accurate research answers*")

current_thread_id = str(st.session_state['thread_id'])
if current_thread_id not in st.session_state['chat_threads']:
    st.session_state['chat_threads'][current_thread_id] = []
for message in st.session_state['chat_threads'][current_thread_id]:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

query = st.chat_input("Ask a question...")

if query:
    with st.chat_message("user"):
        st.markdown(query)

    # 2. Process with LangGraph
    with st.chat_message("assistant"):
        with st.spinner("Researching your question..."):
            try:
                from langchain_core.messages import HumanMessage
                
                # Passing the thread_id config to LangGraph
                config = {"configurable": {"thread_id": current_thread_id}}
                
                # Invoke the graph
                result = app.invoke(
                    {
                        "messages": [HumanMessage(content=query)], 
                        "retry_count": 0
                    }, 
                    config=config
                )
                
                # Get LangSmith run ID
                runs = list(ls_client.list_runs(
                    project_name="Research assistant", 
                    limit=1,
                    is_root=True,
                ))
                if runs:
                    st.session_state.run_id = str(runs[0].id)    

                answer = result["generation"]
                
                # Render answer
                st.markdown(answer)
                
                # Render sources
                if "documents" in result and result["documents"]:
                    with st.expander("View Sources"):
                        for i, doc in enumerate(result["documents"], 1):
                            st.markdown(f"**Source {i}:**")
                            preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                            st.text(preview)
                            st.markdown("---")
                
                if result.get("web_fallback"):
                    st.info("Web search was used to supplement document knowledge")


                # 3 successful, save both messages to history
                st.session_state['chat_threads'][current_thread_id].append({"role": "user", "content": query})
                st.session_state['chat_threads'][current_thread_id].append({"role": "assistant", "content": answer})
                
                # 4 If this is the first successful pair in the chat, update the title!
                if len(st.session_state['chat_threads'][current_thread_id]) == 2:
                    short_title = query[:25] + "..." if len(query) > 25 else query
                    st.session_state['thread_titles'][current_thread_id] = short_title

            except FileNotFoundError:
                st.error("No vector database found. Please upload documents and click 'Index Documents' in the sidebar.")
            except Exception as e:
                # If it fails, the error shows, but nothing is saved to history!
                st.error(f"An error occurred: {str(e)}")


# feedback
if st.session_state.run_id and len(st.session_state['chat_threads'][current_thread_id]) > 0:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("👍"):
            ls_client.create_feedback(st.session_state.run_id, key="user-feedback", score=1)
            st.toast("Thanks for the feedback!")
    with col2:
        if st.button("👎"):
            ls_client.create_feedback(st.session_state.run_id, key="user-feedback", score=0)
            st.toast("Feedback recorded!")