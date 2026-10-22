#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡综合后端服务
1. 托管前端静态网站 (frontend/ 静态文件)
2. 提供 RESTful JSON API (/api/flights, /api/calendar, /api/monitor/*)
3. 挂载后台自动化轮询引擎
"""
from __future__ import annotations
import http.server, json, mimetypes, os, sys, urllib.parse
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception: pass

from seccard_client import SecCardClient, CITY_IATA, IATA_CITY
from scheduler import MonitorScheduler

PORT = 3000
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

client = SecCardClient()
scheduler = MonitorScheduler(client)

class AppHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def address_string(self):
        # 禁用反向 DNS 解析，彻底消除 Windows 下 getfqdn 导致的数秒至数十秒卡顿
        return self.client_address[0]

    def log_message(self, format, *args):
        # 控制台即时日志刷新
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}\n")
        sys.stdout.flush()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # ----------------------------- API 路由
        if path == "/api/status":
            self.send_json({
                "ok": True,
                "serverTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hasCredentials": bool(client.headers),
                "lastSyncTime": scheduler.last_sync_time or "未开始",
                "lastSyncStatus": scheduler.last_sync_status,
                "intervalSeconds": scheduler.interval,
                "taskCount": len(scheduler.tasks)
            })
            return

        elif path == "/api/flights":
            # 兼容中文城市名与三字码 (如 杭州 / HGH)
            raw_from = qs.get("from", [""])[0]
            raw_to = qs.get("to", [""])[0]
            date_str = qs.get("date", [""])[0] or datetime.now().strftime("%Y-%m-%d")

            # 尝试通过 IATA_CITY 还原标准城市名
            frm = IATA_CITY.get(raw_from, raw_from)
            to = IATA_CITY.get(raw_to, raw_to)

            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return
            try:
                flights = client.search_flights(frm, to, date_str)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.send_json({
                    "ok": True, 
                    "from": frm, 
                    "to": to, 
                    "date": date_str, 
                    "flights": flights,
                    "count": len(flights),
                    "queryTime": now_str
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif path == "/api/calendar":
            frm = qs.get("from", [""])[0]
            to = qs.get("to", [""])[0]
            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return
            try:
                cal = client.get_calendar(frm, to)
                self.send_json({"ok": True, "from": frm, "to": to, "calendar": cal})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif path == "/api/destinations":
            frm = qs.get("from", ["HGH"])[0]
            try:
                dests = client.get_official_destinations(frm)
                self.send_json({"ok": True, "from": frm, "destinations": dests, "count": len(dests)})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif path == "/api/monitor/tasks":
            self.send_json({
                "ok": True,
                "tasks": scheduler.tasks,
                "lastSyncTime": scheduler.last_sync_time,
                "lastSyncStatus": scheduler.last_sync_status
            })
            return

        elif path == "/api/monitor/history":
            self.send_json({"ok": True, "history": scheduler.history})
            return

        elif path == "/api/patrol/hot-routes":
            hot_file = BACKEND_DIR / "data" / "hot_routes.json"
            routes = []
            if hot_file.exists():
                try:
                    routes = json.loads(hot_file.read_text(encoding="utf-8"))
                except Exception:
                    routes = []
            self.send_json({"ok": True, "routes": routes, "count": len(routes), "max": 30})
            return

        # ----------------------------- 静态资源交给标准库原生高并发流式分发
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if path == "/api/monitor/tasks":
            frm = body.get("from")
            to = body.get("to")
            date_str = body.get("date")
            if not frm or not to or not date_str:
                self.send_json({"ok": False, "error": "缺少 from、to 或 date 字段"}, 400)
                return
            new_task = scheduler.add_task(frm, to, date_str)
            self.send_json({"ok": True, "task": new_task})
            return

        elif path == "/api/monitor/sync":
            # 立即触发一轮同步
            scheduler.sync_once()
            self.send_json({
                "ok": True,
                "message": "已完成即时同步",
                "lastSyncTime": scheduler.last_sync_time,
                "tasks": scheduler.tasks
            })
            return

        elif path == "/api/patrol/hot-routes":
            routes = body.get("routes", [])
            if not isinstance(routes, list):
                self.send_json({"ok": False, "error": "routes 必须是数组"}, 400)
                return
            if len(routes) > 30:
                self.send_json({"ok": False, "error": "巡检航线最多限制 30 条"}, 400)
                return
            cleaned_routes = []
            seen = set()
            for item in routes:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    frm, to = str(item[0]).strip(), str(item[1]).strip()
                    if frm and to and (frm, to) not in seen:
                        seen.add((frm, to))
                        cleaned_routes.append([frm, to])
            hot_file = BACKEND_DIR / "data" / "hot_routes.json"
            hot_file.write_text(json.dumps(cleaned_routes, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_json({"ok": True, "routes": cleaned_routes, "count": len(cleaned_routes), "max": 30})
            return

        self.send_json({"ok": False, "error": f"404 Not Found: {path}"}, 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/monitor/tasks":
            task_id = qs.get("id", [""])[0]
            if not task_id:
                self.send_json({"ok": False, "error": "缺少 id 参数"}, 400)
                return
            success = scheduler.remove_task(task_id)
            self.send_json({"ok": success})
            return

        self.send_json({"ok": False, "error": f"404 Not Found: {path}"}, 404)

def run():
    # 保持调度监控引擎纯待命状态，绝不随服务启动自动跑轮询 (避免打扰官方接口与后台偷跑)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    print("\n=======================================================")
    print(f"✈️ 长龙航空畅飞卡前后端统一服务已启动！")
    print(f"🌐 本地访问地址: http://localhost:{PORT}")
    print(f"📡 实时 API 就绪: http://localhost:{PORT}/api/status")
    print(f"🛡️ 后台自动轮询: 已彻底关闭 (仅响应用户前端点击与按需查票)")
    print("=======================================================\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if scheduler.running:
            scheduler.stop()
        print("\n服务已平稳关闭。")

if __name__ == "__main__":
    run()
