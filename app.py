import streamlit as st
import pandas as pd
import os
import time
import re
import uuid
import streamlit.components.v1 as components
from ydata_profiling import ProfileReport
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# --- IMPORT MODULES ---
from config import WORKSPACE_DIR
from utils import (
    render_images_in_grid,
    get_llm_friendly_summary,
    save_uploaded_file,
    extract_image_from_response,
)
from agent.backend import get_agent_graph

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

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🗂️ Database Connection")
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

# ==========================================
# MAIN INTERFACE
# ==========================================
current_id = st.session_state.current_chat_id
current_chat = st.session_state.chats[current_id]

st.title(f"🤖 Agentic Data Scientist")

# --- STEP 1: UPLOAD ---
with st.expander("📁 Step 1: Upload Data", expanded=(current_chat["df"] is None)):
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key=f"up_{current_id}")

    if uploaded_file and (
        current_chat["df"] is None or current_chat.get("filename") != uploaded_file.name
    ):
        file_path, filename = save_uploaded_file(uploaded_file)
        df = pd.read_csv(file_path)
        current_chat["df"] = df
        current_chat["filename"] = filename

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
            docker_path = f"/app/workspace/{filename}"

            init_prompt = (
                f"SYSTEM EVENT: User uploaded '{filename}'. "
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
                    "content": f"✅ **Data Loaded!** Ready to analyze **{filename}**.",
                }
            )
            status.update(label="Data Ready!", state="complete", expanded=False)
        st.rerun()

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
if prompt := st.chat_input("Ask about correlations, trends..."):
    current_chat["messages"].append({"role": "user", "type": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1. Prepare LangChain Messages
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

        # 2. Stream Agent
        try:
            active_tool_id = None
            for event in st.session_state.agent_graph.stream({"messages": lc_msgs}):
                for node_name, values in event.items():
                    if "messages" in values:
                        for msg in values["messages"]:
                            if isinstance(msg, AIMessage):
                                # THOUGHTS
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

                                # TOOL CALLS
                                if msg.tool_calls:
                                    tool_call = msg.tool_calls[0]
                                    tool_name = tool_call["name"]
                                    tool_args = tool_call["args"]

                                    if tool_name == "docker_python_tool":
                                        code = tool_args.get("code", "")
                                        active_tool_id = tool_call.get(
                                            "id", f"call_{uuid.uuid4().hex[:8]}"
                                        )
                                        with st.expander(
                                            "📝 Executed Python Code", expanded=True
                                        ):
                                            st.code(code, language="python")
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
                                        active_tool_id = tool_call.get(
                                            "id", f"call_{uuid.uuid4().hex[:8]}"
                                        )
                                        with st.expander(
                                            "📝 Executed SQL Query", expanded=True
                                        ):
                                            st.code(query, language="sql")
                                        current_chat["messages"].append(
                                            {
                                                "role": "assistant",
                                                "type": "code",
                                                "language": "sql",
                                                "content": query,
                                                "tool_id": active_tool_id,
                                            }
                                        )

                            elif isinstance(msg, ToolMessage):
                                output = msg.content
                                if "EXECUTION_ERROR:" in output:
                                    st.error("🚨 Code Execution Failed")
                                    with st.expander("🔍 Traceback", expanded=True):
                                        st.code(
                                            output.replace("EXECUTION_ERROR:\n", "")
                                        )
                                else:
                                    with st.expander("📊 Result Output", expanded=True):
                                        clean = re.sub(
                                            r"\[IMAGE_GENERATED:.*?\]", "", output
                                        )
                                        if clean.strip():
                                            st.text(clean)
                                        render_images_in_grid(
                                            extract_image_from_response(output)
                                        )

                                current_chat["messages"].append(
                                    {
                                        "role": "assistant",
                                        "type": "output",
                                        "content": output,
                                    }
                                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
