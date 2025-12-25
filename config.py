import os

# Base directory for the project
BASE_DIR = os.getcwd()

# Workspace for the agent (mounted to Docker)
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")

if not os.path.exists(WORKSPACE_DIR):
    os.makedirs(WORKSPACE_DIR)

# Docker Execution Service URL
DOCKER_EXEC_URL = "http://localhost:5001/execute"

# LLM Configuration
LLM_BASE_URL = "http://localhost:1234/v1"
LLM_API_KEY = "lm-studio"
LLM_MODEL = "openai/gpt-oss-20b"
