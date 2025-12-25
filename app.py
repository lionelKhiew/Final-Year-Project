import streamlit as st
import pandas as pd
import os
import time
import re
import uuid
import streamlit.components.v1 as components
from ydata_profiling import ProfileReport
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import requests  # <--- ADD THIS LINE
from config import WORKSPACE_DIR
from utils import (
    render_images_in_grid,
    get_llm_friendly_summary,
    save_uploaded_file,
    extract_image_from_response,
)
from agent.backend import get_agent_graph
from agent.rag import build_vector_store  # <--- NEW IMPORT


def render_sidebar_guide():
    with st.sidebar.expander("📖 User Guide & Cheat Sheet", expanded=False):

        st.markdown("### 🚀 How to Start")
        st.markdown(
            """
            1. **Upload Data:** Drag & drop your CSV (for Analysis) and PDFs (for Knowledge).
            2. **Connect DB:** Wait for the system to ingest the data.
            3. **Ask Questions:** Chat with the agent naturally.
            """
        )

        st.divider()

        st.markdown("### 🤖 Example Prompts")

        st.caption("📊 **Data Science (Python + Plotting)**")
        st.code(
            "Analyze the correlation between Age and Balance. Show a heatmap.",
            language="text",
        )
        st.code(
            "Train a Random Forest model to predict Churn. Show the confusion matrix.",
            language="text",
        )

        st.caption("🧠 **RAG (Knowledge Base)**")
        st.code("What is the bank's policy on 'High Value Churn'?", language="text")
        st.code(
            "According to the documents, what does 'Exited=1' mean?", language="text"
        )

        st.caption("🗄️ **Database (SQL)**")
        st.code("How many customers are Active Members?", language="text")
        st.code("List top 5 customers by EstimatedSalary.", language="text")

        st.divider()

        st.markdown("### ℹ️ Legend")
        st.info("✅ **Green:** Knowledge retrieved from Policy (RAG).")
        st.warning("📊 **Gray/Code:** Python Analysis running in Docker.")
        st.error("🔄 **Restart:** Use if the Agent gets stuck.")


# --- Helper Function to Save Files ---
def save_uploaded_file(uploaded_file, folder="workspace"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path, uploaded_file.name


# --- CONFIGURATION ---
st.set_page_config(page_title="Agentic Data Scientist", page_icon="🤖", layout="wide")

if "db_uri" not in st.session_state:
    st.session_state.db_uri = None

# Initialize Agent
if "agent_graph" not in st.session_state:
    st.session_state.agent_graph = get_agent_graph(st.session_state.db_uri)

# --- SESSION STATE ---
if "chats" not in st.session_state:
    st.session_state.chats = {
        "default": {
            "title": "New Chat",
            "messages": [],
            "df": None,
            "report_html_path": None,
        }
    }
    st.session_state.current_chat_id = "default"

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("💡 By Khiew Jit Chen")
    render_sidebar_guide()

    st.divider()

    with st.expander("🔌 Postgres in Docker", expanded=False):
        db_user = st.text_input("User ID", value="admin")
        db_pass = st.text_input("Password", type="password", value="password123")
        db_host = st.text_input("Host", value="localhost")
        db_port = st.text_input("Port", value="5432")
        db_name = st.text_input("Database Name", value="banking_system")

        if st.button("🔗 Connect DB", use_container_width=True):
            new_uri = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            try:
                new_agent = get_agent_graph(new_uri)
                st.session_state.agent_graph = new_agent
                st.session_state.db_uri = new_uri
                st.success("Connected!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Connection Failed: {e}")

        if st.session_state.db_uri:
            st.caption(f"✅ Active: `{st.session_state.db_uri.split('@')[-1]}`")
        else:
            st.caption("❌ Disconnected")

    st.divider()

    with st.expander("🧹 Workspace Management", expanded=False):
        if st.button("🗑️ Clear Workspace", use_container_width=True):
            for f in os.listdir(WORKSPACE_DIR):
                file_path = os.path.join(WORKSPACE_DIR, f)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    st.error(f"Error deleting {f}: {e}")
            st.success("Workspace cleared!")
            time.sleep(1)
            st.rerun()

        # --- Restart Kernel Button ---
        if st.button("🔄 Restart Python Kernel", use_container_width=True):
            try:
                # Send request to Docker
                response = requests.post("http://localhost:5000/restart", timeout=5)

                if response.status_code == 200:
                    st.toast("✅ Kernel Restarted Successfully!", icon="🔄")
                    # Optional: Add a system message to chat history
                    st.session_state.chats[st.session_state.current_chat_id][
                        "messages"
                    ].append(
                        {
                            "role": "assistant",
                            "type": "text",
                            "content": "🔄 **System Notification:** Python Kernel has been restarted. Memory cleared.",
                        }
                    )
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to restart: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

# ==========================================
# MAIN INTERFACE
# ==========================================
current_id = st.session_state.current_chat_id
current_chat = st.session_state.chats[current_id]

st.title(f"🤖 Agentic Data Scientist")

# --- STEP 1: UPLOAD ---
# --- STEP 1: UPLOAD DATA & KNOWLEDGE ---
with st.expander("📁 Step 1: Upload Data & Knowledge", expanded=True):

    # Create two columns layout
    c1, c2 = st.columns(2)

    # === COLUMN 1: CSV DATA (For SQL Database) ===
    with c1:
        st.subheader("📊 Structured Data")
        uploaded_file = st.file_uploader(
            "Upload CSV (external dataset)", type=["csv"], key="csv_uploader"
        )

        if uploaded_file and not st.session_state.get("db_active", False):
            # --- CHANGE HERE: Save to 'workspace' ---
            file_path, file_name = save_uploaded_file(uploaded_file, folder="workspace")
            df = pd.read_csv(file_path)
            current_chat["df"] = df
            current_chat["file_name"] = file_name

            with st.status("🚀 Processing Data...", expanded=True) as status:
                if len(df) > 5000:
                    profile_df = df.sample(n=5000, random_state=42)
                else:
                    profile_df = df

                pr = ProfileReport(profile_df, explorative=False, minimal=True)
                report_path = os.path.join(WORKSPACE_DIR, f"report_{current_id}.html")
                pr.to_file(report_path)
                current_chat["report_html_path"] = report_path

                st.write("Priming Agent...")
                data_summary = get_llm_friendly_summary(df)
                docker_path = f"/app/workspace/{file_name}"

                init_prompt = (
                    f"SYSTEM EVENT: User uploaded '{file_name}'. "
                    f"1. Auto-load it: `df = pd.read_csv('{docker_path}')`. "
                    f"2. DATA SUMMARY:\n{data_summary}\n\n"
                    f"Acknowledge readiness."
                )
                st.session_state.agent_graph.invoke(
                    {"messages": [HumanMessage(content=init_prompt)]}
                )

                current_chat["messages"].append(
                    {
                        "role": "assistant",
                        "type": "text",
                        "content": f"✅ **Data Loaded!** Ready to analyze **{file_name}**.",
                    }
                )
                status.update(label="Data Ready!", state="complete", expanded=False)
                st.session_state["db_active"] = True
            st.rerun()

    # === COLUMN 2: KNOWLEDGE BASE (For RAG) ===
    with c2:
        st.subheader("🧠 Domain Knowledge")
        kb_files = st.file_uploader(
            "Upload Policies (PDF/TXT)",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            key="rag_uploader",
        )

        # Check if files are uploaded AND vector store is empty
        if kb_files and st.session_state.vector_store is None:
            with st.spinner("Processing Knowledge Base..."):
                kb_paths = []
                for f in kb_files:
                    # --- CHANGE HERE: Save to 'knowledge_base' folder ---
                    path, _ = save_uploaded_file(f, folder="knowledge_base")
                    kb_paths.append(path)

                # 1. Build the Vector Store (Reads from knowledge_base/)
                st.session_state.vector_store = build_vector_store(kb_paths)

                # 2. Re-Initialize Agent with the NEW Brain
                st.session_state.agent_graph = get_agent_graph(
                    db_uri=st.session_state.get("db_uri"),
                    vector_store=st.session_state.vector_store,
                )

                st.success(
                    f"✅ Ingested {len(kb_files)} documents from 'knowledge_base/'!"
                )

# --- STEP 2: REPORT ---
if current_chat["report_html_path"] and os.path.exists(
    current_chat["report_html_path"]
):
    with st.expander("📊 Step 2: View Profile Report", expanded=False):
        with open(current_chat["report_html_path"], "r", encoding="utf-8") as f:
            components.html(f.read(), height=800, scrolling=True)

st.divider()

# --- STEP 3: CHAT RENDER ---
st.subheader("💬 Step 3: Chat with your Data")

for msg in current_chat["messages"]:
    if msg.get("type") == "code":
        lang = msg.get("language", "python")
        label = (
            "📝 Executed Python Code" if lang == "python" else "📝 Executed SQL Query"
        )
        with st.chat_message("assistant"):
            with st.expander(label, expanded=False):
                st.code(msg["content"], language=lang)

    elif msg.get("type") == "output":
        with st.chat_message("assistant"):
            # Check if this output came from the RAG Tool (Bank Policy)
            # We assume we saved 'tool_name' in the history (see Part 2 below)
            if "search_bank_policy" in msg.get("tool_name", ""):
                with st.status("📚 Checked Knowledge Base", state="complete"):
                    st.info("✅ Retrieved relevant information from Bank Policy.")
                    with st.expander("View Source Text"):
                        st.text(msg["content"])

            # Otherwise, assume it's Python/Data Output (Show Charts)
            else:
                with st.expander("📊 Result Output", expanded=False):
                    images = extract_image_from_response(msg["content"])
                    clean_out = re.sub(r"\[IMAGE_GENERATED:.*?\]", "", msg["content"])
                    if clean_out.strip():
                        st.text(clean_out)
                    render_images_in_grid(images)

    else:
        if msg["content"] and msg["content"].strip():
            with st.chat_message(msg["role"]):
                images = extract_image_from_response(msg["content"])
                clean_text = re.sub(r"\[IMAGE_GENERATED:.*?\]", "", msg["content"])
                st.markdown(clean_text)
                render_images_in_grid(images)

# --- STEP 4: INPUT & LOGIC ---
# --- STEP 4: INPUT & LOGIC ---
if prompt := st.chat_input("Ask about correlations, trends..."):
    # 1. Append User Message
    current_chat["messages"].append({"role": "user", "type": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 2. Prepare LangChain Messages
        lc_msgs = []
        last_tool_id = None

        for i, m in enumerate(current_chat["messages"][:-1]):
            if m["role"] == "user":
                lc_msgs.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                if m["type"] == "text":
                    lc_msgs.append(AIMessage(content=m["content"]))
                elif m["type"] == "code":
                    t_id = m.get("tool_id", f"call_{i}")
                    last_tool_id = t_id
                    lc_msgs.append(
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "docker_python_tool",
                                    "args": {"code": m["content"]},
                                    "id": t_id,
                                }
                            ],
                        )
                    )
                elif m["type"] == "output":
                    if last_tool_id:
                        lc_msgs.append(
                            ToolMessage(tool_call_id=last_tool_id, content=m["content"])
                        )

        lc_msgs.append(HumanMessage(content=prompt))

        # 3. Stream Agent
        try:
            active_tool_id = None
            last_tool_name = None  # <--- NEW: Track which tool is running

            for event in st.session_state.agent_graph.stream({"messages": lc_msgs}):
                for node_name, values in event.items():
                    if "messages" in values:
                        for msg in values["messages"]:

                            # --- A. AI DECISION (Thoughts & Tool Calls) ---
                            if isinstance(msg, AIMessage):
                                # Display Thoughts
                                if msg.content and (
                                    not current_chat["messages"]
                                    or current_chat["messages"][-1]["content"]
                                    != msg.content
                                ):
                                    st.markdown(f"💭 **Thought:** {msg.content}")
                                    current_chat["messages"].append(
                                        {
                                            "role": "assistant",
                                            "type": "text",
                                            "content": msg.content,
                                        }
                                    )

                                # Handle Tool Calls
                                if msg.tool_calls:
                                    tool_call = msg.tool_calls[0]
                                    tool_name = tool_call["name"]
                                    tool_args = tool_call["args"]
                                    last_tool_name = tool_name  # <--- Capture the name!

                                    active_tool_id = tool_call.get(
                                        "id", f"call_{uuid.uuid4().hex[:8]}"
                                    )

                                    # Display Logic based on Tool Type
                                    if tool_name == "docker_python_tool":
                                        code = tool_args.get("code", "")
                                        with st.expander(
                                            "📝 Executed Python Code", expanded=True
                                        ):
                                            st.code(code, language="python")

                                        # Save Code to History
                                        current_chat["messages"].append(
                                            {
                                                "role": "assistant",
                                                "type": "code",
                                                "language": "python",
                                                "content": code,
                                                "tool_id": active_tool_id,
                                            }
                                        )

                                    elif tool_name == "sql_db_query":
                                        query = tool_args.get("query", "")
                                        with st.expander(
                                            "📝 Executed SQL Query", expanded=True
                                        ):
                                            st.code(query, language="sql")

                                        # Save SQL to History
                                        current_chat["messages"].append(
                                            {
                                                "role": "assistant",
                                                "type": "code",
                                                "language": "sql",
                                                "content": query,
                                                "tool_id": active_tool_id,
                                            }
                                        )

                            # --- B. TOOL OUTPUT (Results) ---
                            elif isinstance(msg, ToolMessage):
                                output = msg.content

                                if "EXECUTION_ERROR:" in output:
                                    st.error("🚨 Code Execution Failed")
                                    with st.expander("🔍 Traceback", expanded=True):
                                        st.code(
                                            output.replace("EXECUTION_ERROR:\n", "")
                                        )
                                else:
                                    # 1. RAG OUTPUT (Hide Text)
                                    if (
                                        last_tool_name
                                        and "search_bank_policy" in last_tool_name
                                    ):
                                        with st.status(
                                            "📚 Checking Knowledge Base...",
                                            state="complete",
                                        ):
                                            st.info(
                                                "✅ Found relevant info in Bank Policy."
                                            )
                                            with st.expander("View Source Details"):
                                                st.text(output)

                                    # 2. PYTHON OUTPUT (Show Charts)
                                    else:
                                        with st.expander(
                                            "📊 Result Output", expanded=True
                                        ):
                                            clean = re.sub(
                                                r"\[IMAGE_GENERATED:.*?\]", "", output
                                            )
                                            if clean.strip():
                                                st.text(clean)
                                            render_images_in_grid(
                                                extract_image_from_response(output)
                                            )

                                # Save Output to History (WITH TOOL NAME)
                                current_chat["messages"].append(
                                    {
                                        "role": "assistant",
                                        "type": "output",
                                        "content": output,
                                        "tool_name": last_tool_name,  # <--- Important for history rendering
                                    }
                                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
