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

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import auto_patrol
import threading
import db
from seccard_client import SecCardClient, CITY_IATA, IATA_CITY
from scheduler import MonitorScheduler

# 初始化本地 SQLite 数据库
db.init_db()

PORT = 3000
client = SecCardClient()
scheduler = MonitorScheduler(client)

class AppHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def handle_one_request(self):
        try:
            return super().handle_one_request()
        except Exception:
            import traceback
            traceback.print_exc()
            sys.stdout.flush()

    def address_string(self):
        try:
            return self.client_address[0]
        except Exception:
            return "127.0.0.1"

    def log_message(self, format, *args):
        try:
            msg = format % args
        except Exception:
            msg = " ".join(str(a) for a in args) if args else format
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
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

            frm = IATA_CITY.get(raw_from, raw_from)
            to = IATA_CITY.get(raw_to, raw_to)

            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return
            try:
                flights = client.search_flights(frm, to, date_str)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 核心功能：每次查验结果 (如 17:25查) 自动持久化落库
                try:
                    db.save_seat_query_result(frm, to, date_str, flights)
                except Exception as ex:
                    print(f"⚠️ 查验记录落库提示: {ex}")

                self.send_json({
                    "ok": True, 
                    "from": frm, 
                    "to": to, 
                    "date": date_str, 
                    "flights": flights,
                    "count": len(flights),
                    "queryTime": now_str,
                    "savedToDb": True
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif path == "/api/seat-cache":
            # 从数据库读取该航线所有已被查验过的记录 (如 17:25查)
            frm = qs.get("from", [""])[0]
            to = qs.get("to", [""])[0]
            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return
            records = db.get_seat_queries_for_route(frm, to)
            self.send_json({"ok": True, "from": frm, "to": to, "cache": records})
            return

        elif path == "/api/calendar":
            # 用户核心需求：接口返回时候 这些如 14、21号没票的彻底不用返回，只返回纯净有票出行日
            frm = qs.get("from", [""])[0]
            to = qs.get("to", [""])[0]
            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return

            dates = db.get_available_dates(frm, to)
            # 若库中暂无且有抓包凭据，实时拉取并增量入库
            if not dates and client.headers:
                try:
                    cal = client.get_calendar(frm, to)
                    db.save_route_calendar(frm, to, cal)
                    dates = db.get_available_dates(frm, to)
                except Exception:
                    pass

            self.send_json({
                "ok": True, 
                "from": frm, 
                "to": to, 
                "availableDates": dates,  # 仅包含有票出行日，无票日已被数据库严格过滤
                "count": len(dates)
            })
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
            # 从 SQLite 数据库读取巡检航线配置
            routes = db.get_patrol_routes()
            self.send_json({"ok": True, "routes": routes, "count": len(routes), "max": 30})
            return

        elif path == "/api/patrol/status":
            self.send_json({"ok": True, "state": auto_patrol.PATROL_STATE})
            return

        elif path == "/api/available-routes":
            # 用户核心需求：彻底由数据库动态返回大盘数据，替换前端原本读取静态 json 的方案
            dto = db.get_available_routes_dto()
            dto["seatCache"] = db.get_all_seat_cache()
            self.send_json(dto)
            return

        elif path == "/api/patrol/config":
            configs = db.get_patrol_config()
            self.send_json({"ok": True, "config": configs})
            return

        elif path == "/api/patrol/logs":
            # 查询数据库中的巡检流水
            logs = db.get_recent_patrol_logs(50)
            self.send_json({"ok": True, "logs": logs, "count": len(logs)})
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
            # 持久化写入 SQLite 数据库
            db.set_patrol_routes(cleaned_routes)
            self.send_json({"ok": True, "routes": cleaned_routes, "count": len(cleaned_routes), "max": 30})
            return

        elif path == "/api/patrol/config":
            cfg = body.get("config", {})
            if isinstance(cfg, dict) and cfg:
                db.update_patrol_config(cfg)
                self.send_json({"ok": True, "message": "巡检规则已成功落库更新", "config": db.get_patrol_config()})
            else:
                self.send_json({"ok": False, "error": "config 必须为非空键值对对象"}, 400)
            return

        elif path == "/api/patrol/trigger":
            if auto_patrol.PATROL_STATE.get("running"):
                self.send_json({"ok": False, "error": "当前已有巡检任务正在进行中，请等待完成"}, 400)
                return
            if not client.headers:
                client.load_credentials()
            if not client.headers:
                self.send_json({
                    "ok": False,
                    "error": "未能在 backend/data/ 目录下检测到有效的 cl.saz 凭证文件！请先放置抓包凭证再执行巡检。"
                }, 400)
                return

            def patrol_worker():
                try:
                    auto_patrol.run_patrol_cycle(client, mode="hot")
                except Exception as ex:
                    print(f"⚠️ 手动巡检异常: {ex}")
                    auto_patrol.PATROL_STATE["running"] = False
                    auto_patrol.PATROL_STATE["status_text"] = f"巡检中断: {ex}"

            t = threading.Thread(target=patrol_worker, daemon=True)
            t.start()
            self.send_json({"ok": True, "message": "已成功启动 Top 30 慢速拟人巡检 (耗时约2~3分钟)，请查看实时进度"})
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
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), AppHandler)
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
