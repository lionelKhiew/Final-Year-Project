import os
import queue
import re
import base64
import time
import jupyter_client
from subprocess import PIPE


class AgentKernel:
    def __init__(self, work_dir="./workspace"):
        self.work_dir = work_dir
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        # 启动 Python 内核
        # 这里的 'python3' 对应你环境里安装的 ipykernel
        self.kernel_manager = jupyter_client.KernelManager(kernel_name="python3")
        self.kernel_manager.start_kernel(stdout=PIPE, stderr=PIPE)
        self.kernel = self.kernel_manager.blocking_client()
        self.kernel.start_channels()

        # 等待内核就绪
        try:
            self.kernel.wait_for_ready(timeout=10)
            print("--- Python Kernel Ready ---")
        except RuntimeError:
            print("--- Kernel Failed to Start ---")

    def execute(self, code):
        self.kernel.execute(code)
        msg_list = []

        # 简单的超时控制
        start_time = time.time()
        while True:
            try:
                iopub_msg = self.kernel.get_iopub_msg(timeout=30)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except queue.Empty:
                if time.time() - start_time > 30:
                    break
                continue

        # 解析输出
        logs = []
        images = []

        for msg in msg_list:
            msg_type = msg["msg_type"]
            content = msg["content"]

            # 1. 文本输出 (print)
            if msg_type == "stream":
                logs.append(content["text"])

            # 2. 执行结果 (Last line return)
            elif msg_type == "execute_result":
                data = content.get("data", {})
                if "text/plain" in data:
                    logs.append(data["text/plain"])
                self._check_images(data, images)

            # 3. 显示数据 (Matplotlib charts)
            elif msg_type == "display_data":
                data = content.get("data", {})
                if "text/plain" in data:
                    logs.append(data["text/plain"])
                self._check_images(data, images)

            # 4. 错误处理 (Traceback)
            elif msg_type == "error":
                error_text = "\n".join(content["traceback"])
                # 去除颜色代码，因为 LLM 看不懂 ANSI 颜色
                ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
                clean_error = ansi_escape.sub("", error_text)
                logs.append(f"Error:\n{clean_error}")

        # 格式化返回给 Agent 的结果
        final_output = "\n".join(logs)
        if images:
            final_output += (
                f"\n[System]: Generated {len(images)} image(s): {', '.join(images)}"
            )

        return (
            final_output
            if final_output.strip()
            else "Executed successfully (No output)."
        )

    def _check_images(self, data, image_list):
        # 辅助函数：保存 base64 图片
        for mime in ["image/png", "image/jpeg"]:
            if mime in data:
                ext = "png" if "png" in mime else "jpg"
                filename = f"{int(time.time() * 1000)}.{ext}"
                filepath = os.path.join(self.work_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(data[mime]))
                image_list.append(filepath)

    def shutdown(self):
        self.kernel_manager.shutdown_kernel(now=True)
