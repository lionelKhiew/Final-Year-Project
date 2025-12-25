import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from agent.tools import docker_python_tool, create_rag_tool
from agent.prompts import get_system_prompt


def get_agent_graph(db_uri=None, vector_store=None):
    # 1. Setup LLM
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0,
    )

    # 2. Database Tools (Dynamic)
    sql_tools = []
    db_status = "INACTIVE"
    docker_friendly_uri = None

    if db_uri:
        try:
            # A. Connect Streamlit to DB (Uses localhost)
            db = SQLDatabase.from_uri(db_uri)
            sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
            sql_tools = sql_toolkit.get_tools()
            db_status = "ACTIVE"

            # B. Create the Internal URI for the Agent
            # Replace 'localhost' with 'db' for Docker container networking
            docker_friendly_uri = db_uri.replace("localhost", "db").replace(
                "127.0.0.1", "db"
            )
        except Exception as e:
            st.error(f"⚠️ DB Connection Failed in Backend: {e}")
            sql_tools = []

    # 3. RAG Tool (Using the Factory)
    rag_tools = []
    if vector_store:
        retriever = vector_store.as_retriever()
        # Call the factory function to get the tool
        rag_tools = [create_rag_tool(retriever)]

    # 3. Combine Tools
    all_tools = sql_tools + [docker_python_tool] + rag_tools

    # 4. System Prompt
    # 4. Get System Prompt String (Do not wrap in SystemMessage yet)
    system_prompt_str = get_system_prompt(db_status, docker_friendly_uri)

    # 5. Create Agent (Pass the string directly)
    return create_agent(llm, all_tools, system_prompt=system_prompt_str)
