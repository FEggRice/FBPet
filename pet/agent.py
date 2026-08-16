"""FBeePet 对话入口：把 FBeePet/ 目录里的 FBeePet Agent 作为子进程拉起。

右键菜单点「对话」→ 桌宠在后台启动 uvicorn(子进程)并打开浏览器 127.0.0.1:8000。
DeepSeek API key 由用户在网页端「设置 -> 模型提供商」输入，只存服务进程内存、
不落盘，随桌宠退出一起清空。启动前 seed_deepseek.py 幂等地把默认模型固定成
deepseek-chat 并清掉磁盘上的残留 key。退出桌宠时一起终止服务进程。
"""
from __future__ import annotations

import os
import subprocess
import threading
import urllib.request
import webbrowser
from urllib.error import HTTPError, URLError

POLL_TIMEOUT = 30.0   # 等端口就绪的最长时间(秒)
POLL_INTERVAL = 0.5   # 轮询间隔


class AgentLauncher:
    # FBeePet 子进程管理器：is_running 探活 → launch 启动(含 seed) → open_ui 开浏览器
    # → stop 用 taskkill 杀进程树。spawn 在主线程做(快)，端口轮询放 daemon 线程

    def __init__(self, agent_cfg: dict, base_dir: str) -> None:
        # 从桌宠配置读取 host/port/python/dir，dir 相对桌宠基目录解析成 FBeePet 绝对路径。
        # API key 由用户在网页端输入，不进桌宠配置，这里无需读取。
        self.host = agent_cfg.get("host", "127.0.0.1")
        self.port = int(agent_cfg.get("port", 8000))
        self.python = agent_cfg.get("python") or "python"
        self.dir = os.path.join(base_dir, agent_cfg.get("dir", "FBeePet"))
        self._proc: subprocess.Popen | None = None
        self.url = f"http://{self.host}:{self.port}"

    # -- 探活 ---------------------------------------------------------------

    def is_running(self) -> bool:
        # 端口有 HTTP 响应就认为服务已在跑(无论是不是我们起的，直接复用它)
        try:
            with urllib.request.urlopen(self.url, timeout=1.0):
                return True
        except HTTPError:
            return True  # 有 HTTP 响应即活着(哪怕 404/500)
        except (URLError, OSError):
            return False

    # -- 启动 ---------------------------------------------------------------

    def launch(self) -> None:
        # 启动 FBeePet：先跑 seed(把 provider 固定成 deepseek、清掉磁盘残留 key)，
        # 再以子进程跑 uvicorn，日志追加到 FBeePet.log。key 由用户网页端输入。
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"

        seed = os.path.join(self.dir, "seed_deepseek.py")
        if os.path.exists(seed):
            subprocess.run([self.python, seed], cwd=self.dir, env=env,
                           capture_output=True, timeout=90)

        log_path = os.path.join(self.dir, "FBeePet.log")
        logf = open(log_path, "a", encoding="utf-8")
        self._proc = subprocess.Popen(
            [self.python, "-m", "uvicorn", "backend.app:app",
             "--host", self.host, "--port", str(self.port)],
            cwd=self.dir, env=env, stdin=subprocess.DEVNULL,
            stdout=logf, stderr=subprocess.STDOUT,
        )

    # -- 打开界面 -----------------------------------------------------------

    def open_ui(self) -> None:
        # 后台线程轮询端口，就绪后打开浏览器；超时只记日志不打断
        threading.Thread(target=self._wait_and_open, daemon=True).start()

    def _wait_and_open(self) -> None:
        # 轮询端口直到有响应，然后打开浏览器
        import time

        deadline = time.time() + POLL_TIMEOUT
        while time.time() < deadline:
            if self.is_running():
                webbrowser.open(self.url)
                return
            time.sleep(POLL_INTERVAL)
        print(f"FBeePet: {self.url} 未在 {POLL_TIMEOUT:.0f}s 内就绪，请手动打开")

    # -- 停止 ---------------------------------------------------------------

    def stop(self) -> None:
        # 随桌宠退出终止服务进程树(uvicorn 可能有 reload 子进程，用 taskkill /T)
        if self._proc is None:
            return
        pid = self._proc.pid
        self._proc = None
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
