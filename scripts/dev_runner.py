#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡前后端统一运行器 (单终端版)
在一个终端窗口中同时托管 Python 后端 (3000) 与 Vite 前端 (8173)，
按 Ctrl+C 一键同步退出，不再弹多个黑框。
"""
import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_DIR = ROOT_DIR / "backend"

def clean_ports():
    """清理 3000 与 8173 端口占用"""
    for port in (3000, 8173):
        try:
            # 查找占用端口的 PID
            output = subprocess.check_output(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != os.getpid():
                        subprocess.run(
                            f"taskkill /F /PID {pid}",
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
        except Exception:
            pass

def main():
    print("=" * 60)
    print("  ✈️ 长龙航空畅飞卡服务 (单终端集成模式)")
    print("  🌐 前端大盘: http://localhost:8173")
    print("  📡 后端 API:  http://localhost:3000")
    print("  按 Ctrl+C 可一键停止全部服务")
    print("=" * 60)

    clean_ports()

    # 1. 启动 Python 后端子进程
    backend_proc = subprocess.Popen(
        [sys.executable, str(BACKEND_DIR / "server.py")],
        cwd=str(ROOT_DIR)
    )

    # 2. 启动 Vite 前端子进程
    # Windows 下通过 cmd /c npm run dev 启动
    frontend_proc = subprocess.Popen(
        "npm run dev",
        cwd=str(FRONTEND_DIR),
        shell=True
    )

    # 3. 延时自动在默认浏览器中打开页面
    def open_browser():
        time.sleep(1.8)
        try:
            subprocess.run("start http://localhost:8173", shell=True)
        except Exception:
            webbrowser.open("http://localhost:8173")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    def get_backend_mtime():
        max_t = 0
        for p in BACKEND_DIR.glob("**/*.py"):
            try:
                t = p.stat().st_mtime
                if t > max_t: max_t = t
            except Exception: pass
        return max_t

    last_mtime = get_backend_mtime()

    try:
        # 守护等待子进程，并自动监听后端 py 文件变更实现热重载
        while True:
            # 1. 监测后端代码修改 -> 自动热重启
            cur_mtime = get_backend_mtime()
            if cur_mtime > last_mtime:
                last_mtime = cur_mtime
                print("\n🔄 [热重载] 检测到后端 Python 文件更新，正在秒级自动重启后端...")
                try:
                    if backend_proc.poll() is None:
                        backend_proc.terminate()
                        backend_proc.wait(timeout=2)
                except Exception:
                    backend_proc.kill()
                time.sleep(0.3)
                backend_proc = subprocess.Popen(
                    [sys.executable, str(BACKEND_DIR / "server.py")],
                    cwd=str(ROOT_DIR)
                )
                print("✅ [热重载] 后端服务已自动重启生效！\n")

            if backend_proc.poll() is not None:
                print("\n[!] 后端服务已退出。")
                break
            if frontend_proc.poll() is not None:
                print("\n[!] 前端 Vite 服务已退出。")
                break
            time.sleep(0.6)
    except KeyboardInterrupt:
        print("\n[*] 正在关闭前后端服务...")

    finally:
        # 彻底清理两个子进程及其衍生进程
        try:
            if backend_proc.poll() is None:
                backend_proc.terminate()
                backend_proc.kill()
        except Exception:
            pass

        try:
            if frontend_proc.poll() is None:
                subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        clean_ports()
        print("[-] 服务已平稳退出。\n")

if __name__ == "__main__":
    main()
