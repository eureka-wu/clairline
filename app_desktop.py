#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 智能大盘与航网规划助手 (桌面客户端版)
GitHub 官方仓库: https://github.com/eureka-wu/clairline

特性：
1. 原生轻量：基于 Windows Edge Chromium WebView2 内核，内存占用低至 40MB；
2. 零外部依赖：内置 Python HTTP API 服务与 SQLite 数据引擎，开箱即用；
3. 安全守护：窗口退出时自动还原 Windows 代理，绝不悬挂网络。
"""

import os
import sys
import time
import threading
from pathlib import Path

try:
    import pyi_splash
    pyi_splash.update_text("正在启动本地引擎与航网大盘...")
except ImportError:
    pass

if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    EXE_DIR = Path(__file__).resolve().parent

LOG_DIR = EXE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "clairline_boot.log"

class SafeWriter:
    def __init__(self, target_file=None):
        self.target_file = target_file
    def write(self, s):
        if self.target_file and s:
            try:
                with open(self.target_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(s)
            except Exception:
                pass
    def flush(self):
        pass
    def reconfigure(self, *args, **kwargs):
        pass

if sys.stdout is None:
    sys.stdout = SafeWriter(LOG_PATH)
if sys.stderr is None:
    sys.stderr = SafeWriter(LOG_PATH)

# 兼容普通运行与 PyInstaller 打包环境
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent

BACKEND_DIR = BASE_DIR / "backend"

for p in [str(BACKEND_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import server
except ImportError:
    from backend import server

try:
    import db
except ImportError:
    from backend import db

def cleanup_proxy_if_needed():
    """纯手机号免抓包架构，无需操作 Windows 系统代理"""
    pass

GITHUB_REPO_URL = "https://github.com/eureka-wu/clairline"
APP_TITLE = f"长龙航空 · 畅飞智能助手 {getattr(server, 'APP_VERSION', 'v2.1.3')} (GitHub: eureka-wu/clairline)"

def boot_log(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def find_free_port(start_port: int = 3000, max_tries: int = 30) -> int:
    """动态探测可用未占用端口，彻底避免端口冲突导致闪退"""
    import socket
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_conn:
            s_conn.settimeout(0.15)
            if s_conn.connect_ex(('127.0.0.1', p)) == 0:
                continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p))
                boot_log(f"find_free_port allocated port: {p}")
                return p
            except OSError:
                continue
    return start_port

def show_fatal_error(msg: str):
    """当发生严重致命异常时，弹出系统错误对话框并落盘日志，绝不静默闪退"""
    boot_log(f"FATAL ERROR POPUP: {msg}")
    title = "长龙航空畅飞助手 - 运行异常"
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
        else:
            print(f"[{title}] {msg}", file=sys.stderr)
    except Exception:
        pass

def start_backend_server(port: int = 3000):
    """在后台线程中启动前后端一体化 HTTP 服务"""
    boot_log(f"start_backend_server thread entered, target port={port}")
    try:
        server.PORT = port
        boot_log("calling server.run()...")
        server.run()
        boot_log("server.run() terminated.")
    except Exception as e:
        import traceback
        err = f"后端服务启动异常崩溃: {e}\n\n{traceback.format_exc()}"
        boot_log(err)
        show_fatal_error(err)

def wait_for_server(port: int = 3000, timeout: float = 12.0) -> bool:
    """等待本地后端 HTTP 服务端口就绪，冷启动解压与引擎初始化给予充足时间"""
    import urllib.request
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/status"
    boot_log(f"wait_for_server polling {url} (max timeout={timeout}s)...")
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.8) as resp:
                if resp.status == 200:
                    boot_log(f"wait_for_server SUCCESS in {time.time() - start:.2f}s!")
                    return True
        except Exception:
            time.sleep(0.2)
    boot_log(f"wait_for_server TIMEOUT after {timeout}s!")
    return False

def on_closed():
    """桌面窗口关闭时的退出清理 Hook"""
    boot_log("on_closed triggered, performing cleanup...")
    print("[*] 桌面客户端正在关闭，执行安全退出与代理还原...", flush=True)
    cleanup_proxy_if_needed()
    # 强制退出所有常驻守护线程
    os._exit(0)

def main():
    boot_log("=== main() entered ===")
    try:
        # 1. 初始化数据库与种子航线拓扑
        try:
            db.init_db()
            boot_log("db.init_db() done")
        except Exception as ex:
            boot_log(f"db.init_db() warning: {ex}")
            print(f"[*] 数据库初始化提示: {ex}")

        # 2. 检查并确保系统代理在冷启动时处于关闭正常直连状态
        cleanup_proxy_if_needed()
        boot_log("cleanup_proxy_if_needed() done")

        # 3. 动态分配空闲可用端口（优先 3000，若占用自动向后探测）
        port = find_free_port(3000)

        # 4. 启动后台 HTTP 服务
        server_thread = threading.Thread(target=start_backend_server, args=(port,), daemon=True)
        server_thread.start()
        boot_log(f"server_thread.start() executed for port {port}")

        ready = wait_for_server(port)
        if not ready:
            err_msg = f"本地后端服务引擎在 12 秒内未能成功就绪 (端口 {port})。\n请查看桌面 clairline_boot.log 日志定位具体原因。"
            show_fatal_error(err_msg)
            sys.exit(1)

        # 本地服务已就绪，平滑关闭启动闪屏画面
        try:
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            pass

        # 5. 拉起 WebView2 桌面窗口
        boot_log("Importing webview and creating window...")
        import webview

        window = webview.create_window(
            title=APP_TITLE,
            url=f"http://127.0.0.1:{port}",
            width=1380,
            height=880,
            min_size=(1080, 680),
            text_select=True,
            zoomable=True
        )
        window.events.closed += on_closed

        # 跨平台自适应 Webview 引擎 (Windows 使用 Edge Chromium, macOS 使用原生 Cocoa WebKit)
        gui_engine = "edgechromium" if sys.platform == "win32" else "cocoa"
        try:
            webview.start(gui=gui_engine, debug=False)
        except Exception:
            webview.start(debug=False)
    except Exception:
        import traceback
        err_msg = "长龙航空畅飞助手在启动时遭遇未知异常：\n\n" + traceback.format_exc()
        show_fatal_error(err_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
