# server.py
import os
import queue
import base64
import time
from flask import Flask, request, jsonify
import jupyter_client
from subprocess import PIPE

app = Flask(__name__)


# --- Jupyter Kernel Wrapper ---
class DockerKernel:
    def __init__(self, work_dir="/app/workspace"):
        self.work_dir = work_dir
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        self.kernel_manager = jupyter_client.KernelManager(kernel_name="python3")
        self.kernel_manager.start_kernel(stdout=PIPE, stderr=PIPE)
        self.kernel = self.kernel_manager.blocking_client()
        self.kernel.start_channels()
        self.kernel.wait_for_ready(timeout=10)
        print(f"--- Kernel Ready in {work_dir} ---")

    def execute(self, code):
        self.kernel.execute(code)
        msg_list = []
        start_time = time.time()

        while True:
            try:
                iopub_msg = self.kernel.get_iopub_msg(timeout=5)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except queue.Empty:
                if time.time() - start_time > 10:
                    break
                continue

        logs = []
        images = []

        for msg in msg_list:
            content = msg["content"]
            msg_type = msg["msg_type"]

            if msg_type == "stream":
                logs.append(content["text"])
            elif msg_type in ("execute_result", "display_data"):
                data = content.get("data", {})
                if "text/plain" in data:
                    logs.append(data["text/plain"])

                # Handle Images
                for mime in ["image/png", "image/jpeg"]:
                    if mime in data:
                        ext = "png" if "png" in mime else "jpg"
                        filename = f"{int(time.time() * 1000)}.{ext}"
                        filepath = os.path.join(self.work_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(data[mime]))
                        images.append(filename)
            elif msg_type == "error":
                logs.append(f"Error: {chr(10).join(content['traceback'])}")

        return {"logs": "".join(logs), "images": images}


kernel = DockerKernel()


@app.route("/execute", methods=["POST"])
def execute_endpoint():
    code = request.json.get("code", "")
    return jsonify(kernel.execute(code))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
