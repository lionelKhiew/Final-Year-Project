https://www.youtube.com/watch?v=cjeFeZdarl4# 🤖 Agentic Data Scientist (Final Year Project)

**An autonomous AI Agent capable of performing data science tasks, executing Python code in a sandboxed environment, querying SQL databases, and answering domain-specific questions using RAG.**

> Student: Lionel Khiew / Khiew Jit Chen
> 
> Project Type: Final Year Project

---

## 📖 Overview

This project is an **"Agentic Data Scientist"**—an AI system designed to bridge the gap between non-technical users and complex data analysis. unlike standard chatbots, this agent allows users to upload raw data (CSV) or domain documents (PDF) and interact with them using natural language.

The system features a **Code Interpreter** architecture. When a user asks for a chart or analysis, the agent writes Python code, executes it inside a secure **Docker container**, and returns the actual results (plots, dataframes, or answers).

### ✨ Key Features

1. **📊 Automated Data Analysis:**
   * Upload CSV files for instant profiling (YData Profiling).
   * The Agent generates Python code (Pandas/Matplotlib) to analyze trends and visualize data.
2. **🛡️ Sandboxed Execution:**
   * All generated code runs in an isolated Docker container for security.
   * Persistent workspace allows the agent to save and retrieve files.
3. **🧠 RAG (Retrieval-Augmented Generation):**
   * Upload "Knowledge Base" documents (PDF/TXT/Policies).
   * The agent uses vector search (FAISS) to answer domain-specific questions (e.g., "What is the bank's policy on churn?").
4. **🗄️ SQL Database Integration:**
   * Connects to a PostgreSQL database (running in Docker).
   * Translates natural language questions into SQL queries (Text-to-SQL).
5. **🏠 Privacy-First (Local LLM):**
   * Configured to run with local LLMs (via LM Studio) for data privacy.

---

## 🏗️ Architecture

The system consists of three main components:

1. **Frontend (Streamlit):** The user interface for chat, file uploads, and visualization.
2. **Backend (LangChain):** Manages the reasoning loop, tool selection (SQL vs. Python vs. RAG).
3. **Infrastructure (Docker):**
   * `agent-sandbox`: A Python environment with a Flask server to execute the Agent's code.
   * `db`: PostgreSQL database for structured data.

---

## 🛠️ Prerequisites

Before running the project, ensure you have the following installed:

1. **Docker Desktop** (Required for the sandbox and database).
2. **Python 3.9+** (For the Streamlit frontend).
3. **LM Studio** (Or any OpenAI-compatible local LLM provider).

---

## 🚀 Setup & Installation

### 1. Clone the Repository

**Bash**

```
git clone https://github.com/lionelkhiew/final-year-project.git
cd final-year-project
```

### 2. Configure the Local LLM

This project uses **LM Studio** to serve the LLM locally.

1. Download and install [LM Studio](https://lmstudio.ai/).
2. Load a model (e.g., `Llama 3`, `Mistral`, or `Phi-3`).
3. Start the Local Server on port **1234**.
   * *Note: If you use a different port/provider, update `config.py`.*

### 3. Start Docker Services

This will spin up the **Postgres Database** and the **Python Sandbox Environment**.

**Bash**

```
docker-compose up -d --build
```

*Wait a few moments for the containers to fully initialize.*

### 4. Install Application Dependencies

Install the required libraries for the Streamlit app.

**Bash**

```
pip install -r requirements.txt
```

### 5. Run the Application

**Bash**

```
streamlit run app.py
```

---

## 🖥️ Usage Guide

### A. Data Science Mode

1. Go to **Step 1: Upload Data**.
2. Upload a `.csv` file (e.g., `Churn_Modelling.csv`).
3. The system will generate a profile report.
4. **Chat:** "Show me a correlation heatmap of the data." or "Train a Random Forest model to predict Exited."

### B. Knowledge Base (RAG)

1. Upload policy documents (PDF/TXT) in the **Domain Knowledge** section.
2. **Chat:** "Based on the uploaded documents, what are the requirements for a premium account?"

### C. Database (SQL)

1. Use the Sidebar to connect to the Database (Default credentials provided in `docker-compose.yml`).
2. **Chat:** "How many users in the database are from France?"

---

## 📂 Project Structure

```
final-year-project/
├── agent/                  # Logic for LangChain Agent & Tools
│   ├── backend.py          # Agent initialization
│   ├── rag.py              # Vector Store logic
│   └── tools.py            # Tool definitions (SQL, Python)
├── sandbox/                # Docker Environment for Code Execution
│   ├── Dockerfile          # Sandbox definition
│   └── server.py           # Flask server to receive code
├── knowledge_base/         # Storage for uploaded PDFs
├── workspace/              # Shared volume for generated plots/files
├── app.py                  # Main Streamlit Interface
├── config.py               # Configuration (LLM URL, Paths)
├── docker-compose.yml      # Orchestration for DB and Sandbox
└── requirements.txt        # Python dependencies
```

---

## 📞 Contact

**Lionel Khiew**

* [LinkedIn Profile](https://www.linkedin.com/in/jit-chen-khiew)
* [GitHub Profile](https://www.github.com/lionelKhiew)
* **Demo Video:**
  [YouTube Link](https://www.youtube.com/watch?v=cjeFeZdarl4)

