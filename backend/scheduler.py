#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡自动化调度同步引擎
负责：
1. 监控任务管理（增删查改）
2. 后台定时轮询（可控节奏，模拟人工防封禁）
3. 同步节奏与放票变动日志持久化
"""
from __future__ import annotations
import json, sys, threading, time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception: pass

from seccard_client import SecCardClient, CITY_IATA

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TASKS_FILE = DATA_DIR / "monitor_tasks.json"
HISTORY_FILE = DATA_DIR / "sync_history.json"
CACHE_FILE = DATA_DIR / "flights_cache.json"

class MonitorScheduler:
    def __init__(self, client: SecCardClient):
        self.client = client
        self.interval = 180  # 默认轮询间隔（秒）
        self.running = False
        self.thread: threading.Thread | None = None
        self.tasks: list[dict] = self.load_tasks()
        self.history: list[dict] = self.load_history()
        self.cache: dict = self.load_cache()
        self.last_sync_time: str = ""
        self.last_sync_status: str = "空闲就绪"

    def load_tasks(self) -> list[dict]:
        if TASKS_FILE.exists():
            try: return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        # 预置默认核心监控任务
        default_tasks = [
            {"id": "1", "from": "杭州", "to": "北京", "date": "2026-10-28", "status": "监控中", "lastCheck": "未同步", "stock": "待获取"},
            {"id": "2", "from": "杭州", "to": "阿勒泰", "date": "2026-10-26", "status": "监控中", "lastCheck": "未同步", "stock": "待获取"}
        ]
        self.save_tasks(default_tasks)
        return default_tasks

    def save_tasks(self, tasks: list[dict]):
        self.tasks = tasks
        TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_history(self) -> list[dict]:
        if HISTORY_FILE.exists():
            try: return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return []

    def log_sync(self, target: str, status: str, detail: str, is_change: bool = False):
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target,
            "status": status,
            "detail": detail,
            "isChange": is_change
        }
        self.history.insert(0, entry)
        if len(self.history) > 100:  # 保留最新 100 条
            self.history = self.history[:100]
        HISTORY_FILE.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try: return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {}

    def save_cache(self, key: str, data: any):
        self.cache[key] = {
            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": int(time.time()),
            "data": data
        }
        CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_task(self, from_city: str, to_city: str, date_str: str) -> dict:
        task_id = str(int(time.time() * 1000))[-6:]
        task = {
            "id": task_id,
            "from": from_city,
            "to": to_city,
            "date": date_str,
            "status": "监控中",
            "lastCheck": "刚刚添加",
            "stock": "待获取"
        }
        self.tasks.append(task)
        self.save_tasks(self.tasks)
        return task

    def remove_task(self, task_id: str) -> bool:
        prev_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if len(self.tasks) < prev_len:
            self.save_tasks(self.tasks)
            return True
        return False

    def sync_once(self):
        """执行一轮安全调度的监控轮询"""
        if not self.tasks:
            return
        self.last_sync_status = "正在同步中..."
        for task in self.tasks:
            frm, to, d = task["from"], task["to"], task["date"]
            key = f"{frm}-{to}-{d}"
            try:
                # 查余量
                flights = self.client.search_flights(frm, to, d)
                now_str = datetime.now().strftime("%H:%M:%S")
                task["lastCheck"] = f"刚刚 ({now_str})"
                
                # 统计可兑余量
                total_sec = sum(f["secCardLeft"] for f in flights)
                summary = "、".join(f"{f['flightNo']}余{f['secCardLeft']}" for f in flights) or "当日无航班"
                prev_stock = task.get("stock", "")
                task["stock"] = summary if total_sec > 0 else f"已兑完 ({summary})"
                task["flights"] = flights

                # 缓存
                self.save_cache(key, flights)

                # 记录变动
                is_change = (prev_stock != "待获取" and prev_stock != task["stock"])
                self.log_sync(f"{frm}➔{to} ({d})", "成功", task["stock"], is_change)
                
                # 安全停顿 2 秒，防 Nginx WAF 频率拦截
                time.sleep(2)
            except Exception as e:
                task["lastCheck"] = f"同步异常 ({datetime.now().strftime('%H:%M:%S')})"
                task["status"] = "异常待重试"
                self.log_sync(f"{frm}➔{to} ({d})", "失败", str(e), False)
                time.sleep(3)

        self.save_tasks(self.tasks)
        self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_sync_status = "同步完成"

    def _loop(self):
        # 启动后延时 5 秒再开始后台轮询，确保 Web 服务瞬时秒级就绪
        time.sleep(5)
        while self.running:
            self.sync_once()
            # 分步 sleep 以便能迅速响应停止信号
            for _ in range(self.interval):
                if not self.running: break
                time.sleep(1)

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print(f"🚀 调度引擎已启动，每 {self.interval} 秒自动巡检一次监控目标")

    def stop(self):
        self.running = False
        print("⏹️ 调度引擎已停止")
