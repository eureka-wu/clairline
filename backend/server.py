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
DIST_DIR = FRONTEND_DIR / "dist"
STATIC_DIR = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR
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
        # 优先分发 Vite 构建生成的现代单页应用产物 (dist)
        target_dir = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR
        super().__init__(*args, directory=str(target_dir), **kwargs)

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
        # 静音高频的心跳状态轮询日志，避免控制台刷屏打扰用户
        if "/api/patrol/status" in msg or "/api/status" in msg:
            return
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
            force_refresh = qs.get("refresh", ["0"])[0] in ("1", "true", "True") or qs.get("force", ["0"])[0] in ("1", "true", "True")

            frm = db.normalize_city(raw_from)
            to = db.normalize_city(raw_to)
            from_code = db.normalize_iata(raw_from)
            to_code = db.normalize_iata(raw_to)

            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return

            # 用户核心诉求：存储不存 localStorage 存数据库！优先从数据库读取已查验的记录
            if not force_refresh:
                try:
                    saved_flights = db.get_saved_flight_details(frm, to, date_str)
                    if saved_flights:
                        self.send_json({
                            "ok": True, 
                            "from": frm, 
                            "to": to, 
                            "fromCode": from_code,
                            "toCode": to_code,
                            "date": date_str, 
                            "flights": saved_flights,
                            "count": len(saved_flights),
                            "fromDb": True,
                            "queryTime": saved_flights[0].get("queryTime", ""),
                            "savedToDb": True
                        })
                        return
                except Exception as ex:
                    print(f"⚠️ 读取数据库查验记录提示: {ex}")

            try:
                flights = client.search_flights(from_code, to_code, date_str)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 核心功能：每次查验结果自动持久化落库
                try:
                    db.save_seat_query_result(frm, to, date_str, flights)
                except Exception as ex:
                    print(f"⚠️ 查验记录落库提示: {ex}")

                self.send_json({
                    "ok": True, 
                    "from": frm, 
                    "to": to, 
                    "fromCode": from_code,
                    "toCode": to_code,
                    "date": date_str, 
                    "flights": flights,
                    "count": len(flights),
                    "fromDb": False,
                    "queryTime": now_str,
                    "savedToDb": True
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif path == "/api/seat-cache":
            # 从数据库读取已持久化的查验记录缓存 (支持单航线或全库拉取)
            raw_from = qs.get("from", [""])[0]
            raw_to = qs.get("to", [""])[0]
            frm = db.normalize_city(raw_from)
            to = db.normalize_city(raw_to)
            if frm and to:
                records = db.get_seat_queries_for_route(frm, to)
                self.send_json({
                    "ok": True, 
                    "from": frm, 
                    "to": to, 
                    "fromCode": db.normalize_iata(raw_from),
                    "toCode": db.normalize_iata(raw_to),
                    "cache": records
                })
            else:
                all_records = db.get_all_seat_cache()
                self.send_json({"ok": True, "cache": all_records})
            return

        elif path == "/api/calendar":
            # 用户核心需求：接口返回时候 这些如 14、21号没票的彻底不用返回，只返回纯净有票出行日
            raw_from = qs.get("from", [""])[0]
            raw_to = qs.get("to", [""])[0]
            force_refresh = qs.get("refresh", ["0"])[0] in ("1", "true", "True")

            frm = db.normalize_city(raw_from)
            to = db.normalize_city(raw_to)
            from_code = db.normalize_iata(raw_from)
            to_code = db.normalize_iata(raw_to)

            if not frm or not to:
                self.send_json({"ok": False, "error": "缺少 from 或 to 参数"}, 400)
                return

            # 用户新需求：支持单条航线点击即刻向长龙官方刷新最新可兑日历
            if force_refresh:
                if not client.headers:
                    client.load_credentials()
                if not client.headers:
                    self.send_json({"ok": False, "error": "未检测到有效的 cl.saz 凭证，无法向官方请求！"}, 400)
                    return
                try:
                    client.check_and_reload()
                    cal = client.get_calendar(from_code, to_code)
                    db.save_route_calendar(frm, to, cal)
                except Exception as ex:
                    err_msg = str(ex)
                    if "100001" in err_msg or "403" in err_msg or "未登录" in err_msg:
                        self.send_json({"ok": False, "error": "长龙微信小程序登录态已过期 (100001)，请手机微信查一次票更新 cl.saz"}, 400)
                    else:
                        self.send_json({"ok": False, "error": f"长龙接口请求异常: {err_msg}"}, 500)
                    return

            dates = db.get_available_dates(frm, to)
            # 若库中暂无且有抓包凭据，实时拉取并增量入库
            if not dates and not force_refresh and client.headers:
                try:
                    cal = client.get_calendar(from_code, to_code)
                    db.save_route_calendar(frm, to, cal)
                    dates = db.get_available_dates(frm, to)
                except Exception:
                    pass

            self.send_json({
                "ok": True, 
                "from": frm, 
                "to": to, 
                "fromCode": from_code,
                "toCode": to_code,
                "availableDates": dates,  # 仅包含有票出行日，无票日已被数据库严格过滤
                "count": len(dates),
                "refreshed": force_refresh
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

        elif path == "/api/patrol/times":
            times = db.get_full_patrol_times()
            self.send_json({"ok": True, "times": times})
            return

        elif path == "/api/patrol/switches":
            switches = db.get_patrol_switches()
            self.send_json({"ok": True, "switches": switches})
            return

        elif path == "/api/patrol/logs":
            # 查询数据库中的巡检流水
            logs = db.get_recent_patrol_logs(50)
            self.send_json({"ok": True, "logs": logs, "count": len(logs)})
            return

        # 针对未匹配的 API 请求，直接返回标准 404 JSON，避免落入 SPA 静态 fallback
        if path.startswith("/api/"):
            self.send_json({"ok": False, "error": f"404 API Not Found: {path}"}, 404)
            return

        # ----------------------------- 静态资源分发 (支持 Vite 构建产物与 SPA 路由)
        self.serve_static(path)

    def serve_static(self, rel_path: str):
        target_dir = DIST_DIR if DIST_DIR.exists() else FRONTEND_DIR
        clean_rel = rel_path.lstrip("/").split("?")[0].split("#")[0]
        
        file_path = (target_dir / clean_rel).resolve()
        
        # 安全防御：防止目录穿越
        try:
            file_path.relative_to(target_dir.resolve())
        except ValueError:
            self.send_error(403, "Forbidden")
            return

        # 若请求的是根路径或文件不存在（SPA 路由），fallback 至 index.html
        if not clean_rel or not file_path.exists() or file_path.is_dir():
            file_path = target_dir / "index.html"

        if not file_path.exists():
            self.send_error(404, "index.html not found. Please build frontend first.")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            if file_path.suffix == ".js": mime_type = "application/javascript"
            elif file_path.suffix == ".css": mime_type = "text/css"
            elif file_path.suffix == ".svg": mime_type = "image/svg+xml"
            elif file_path.suffix == ".html": mime_type = "text/html"
            else: mime_type = "application/octet-stream"

        if "text" in mime_type or mime_type in ("application/javascript", "application/json"):
            mime_type += "; charset=utf-8"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.log_message(f"Error serving {file_path}: {e}")

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

        elif path == "/api/patrol/times":
            times = body.get("times", [])
            if isinstance(times, list):
                saved = db.set_full_patrol_times(times)
                self.send_json({"ok": True, "times": saved})
            else:
                self.send_json({"ok": False, "error": "times 必须是数组"}, 400)
            return

        elif path == "/api/patrol/switches":
            hot_enabled = body.get("hot_enabled")
            all_enabled = body.get("all_enabled")
            switches = db.set_patrol_switches(hot_enabled=hot_enabled, all_enabled=all_enabled)
            self.send_json({"ok": True, "switches": switches})
            return

        elif path == "/api/patrol/trigger":
            mode = body.get("mode", "hot")
            if mode not in ["hot", "all"]:
                mode = "hot"
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

            # 启动前健康探针：同步检测微信登录态是否依然存活，过期则直接拦截报错
            try:
                client.check_and_reload()
                client.get_calendar("杭州", "深圳")
            except Exception as auth_err:
                err_text = str(auth_err)
                if "100001" in err_text or "403" in err_text or "未登录" in err_text:
                    self.send_json({
                        "ok": False,
                        "error": "长龙微信小程序登录态已过期 (100001)！请在手机微信中重新点开长龙畅飞卡查一次票，导出新 cl.saz 覆盖即可！"
                    }, 400)
                    return
                else:
                    self.send_json({"ok": False, "error": f"长龙接口网络异常: {err_text}"}, 500)
                    return

            def patrol_worker():
                try:
                    auto_patrol.run_patrol_cycle(client, mode=mode)
                except Exception as ex:
                    print(f"⚠️ 手动巡检异常: {ex}")
                    auto_patrol.PATROL_STATE["running"] = False
                    auto_patrol.PATROL_STATE["status_text"] = f"巡检中断: {ex}"

            t = threading.Thread(target=patrol_worker, daemon=True)
            t.start()
            msg = "已成功启动全网全量普查 (约397条)，请查看实时进度" if mode == "all" else "已成功启动 Top 30 慢速拟人巡检 (耗时约2~3分钟)，请查看实时进度"
            self.send_json({"ok": True, "mode": mode, "message": msg})
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
