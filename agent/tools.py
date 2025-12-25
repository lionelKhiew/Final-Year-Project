import os
import re
import uuid
import time
import requests
import traceback
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config import WORKSPACE_DIR, DOCKER_EXEC_URL
from utils import strip_ansi_codes


class PythonToolInput(BaseModel):
    code: str = Field(
        description="The python code to execute. MUST be a valid python script."
    )


@tool("docker_python_tool", args_schema=PythonToolInput)
def docker_python_tool(code: str) -> str:
    """
    Executes Python code in Docker.
    Uses Robust Set Difference to detect new images (ignores timestamps).
    """
    # 1. Clean the code
    cleaned_code = re.sub(r"^```[a-zA-Z]*\n", "", code.strip())
    cleaned_code = re.sub(r"\n```$", "", cleaned_code)

    # 2. GENERATE MARKER
    exec_id = uuid.uuid4().hex
    marker_print = f"print('__EXECUTION_START_{exec_id}__')"

    # 3. SETUP CODE
    setup_code = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "import pandas as pd\n"
        "import os\n"
        "import sys\n"
        "os.chdir('/app/workspace')\n"
    )
    final_code = (
        setup_code
        + "\n"
        + marker_print
        + "\n"
        + cleaned_code
        + "\n"
        + "sys.stdout.flush()"
    )

    try:
        files_before = set(os.listdir(WORKSPACE_DIR))
    except Exception:
        files_before = set()

    try:
        response = requests.post(DOCKER_EXEC_URL, json={"code": final_code}, timeout=45)
        data = response.json()

        # --- LOG PARSING ---
        raw_logs = strip_ansi_codes(data.get("logs", ""))
        marker_str = f"__EXECUTION_START_{exec_id}__"

        if marker_str in raw_logs:
            logs = raw_logs.split(marker_str)[1].lstrip()
        else:
            logs = raw_logs

        if "error" in data and data["error"]:
            clean_err = strip_ansi_codes(data["error"])
            return f"EXECUTION_ERROR:\n{clean_err}"

        time.sleep(1)

        try:
            files_after = set(os.listdir(WORKSPACE_DIR))
        except Exception:
            files_after = set()

        new_files = files_after - files_before
        valid_images = [
            f
            for f in new_files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".svg"))
        ]

        output = logs
        if valid_images:
            img_str = ", ".join(valid_images)
            output += f"\n[IMAGE_GENERATED:{img_str}]"
        elif not logs.strip() and not valid_images:
            return "Success (Code Executed, No Text Output)"

        return output if output.strip() else "Success (No Output)"

    except Exception:
        raw_trace = traceback.format_exc()
        clean_trace = strip_ansi_codes(raw_trace)
        return f"EXECUTION_ERROR:\n{clean_trace}"
