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

if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS).resolve()
    BACKEND_DIR = BUNDLE_DIR / "backend"
    PROJECT_DIR = BUNDLE_DIR
    FRONTEND_DIR = BUNDLE_DIR / "frontend"
    DIST_DIR = FRONTEND_DIR / "dist"
else:
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
import mcp_server
from seccard_client import SecCardClient, CITY_IATA, IATA_CITY
from scheduler import MonitorScheduler

AUTH_EXPIRED = False

def mark_auth_expired():
    global AUTH_EXPIRED
    AUTH_EXPIRED = True

def clear_auth_expired():
    global AUTH_EXPIRED
    AUTH_EXPIRED = False

def get_auth_status() -> dict:
    prof = db.get_user_profile() or {}
    token = prof.get("token") or ""
    update_time = prof.get("updated_at") or ""
    auth_preview = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else (token or "无凭证")
    
    mobile = prof.get("mobile", "")
    masked_mobile = f"{mobile[:3]}****{mobile[-4:]}" if len(mobile) == 11 else (mobile or "")
    
    cert = prof.get("cert_number", "")
    masked_cert = f"{cert[:6]}********{cert[-4:]}" if len(cert) > 10 else (cert or "")
    
    has_profile = bool(mobile or prof.get("user_name"))
    
    # 判定是否过期：若距离上次成功保活超过 25 分钟，主动向长龙网关发起一次实时探针校验
    is_expired = False
    if AUTH_EXPIRED and has_profile:
        is_expired = True
    elif token and update_time:
        try:
            dt = datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")
            diff_minutes = (datetime.now() - dt).total_seconds() / 60.0
            if diff_minutes >= 25.0:
                from loongair_client import keepalive_session
                ka_res = keepalive_session()
                if ka_res.get("ok"):
                    clear_auth_expired()
                    prof = db.get_user_profile() or prof
                    update_time = prof.get("updated_at") or update_time
                elif ka_res.get("expired"):
                    mark_auth_expired()
                    is_expired = True
        except Exception:
            pass

    is_logged_in = bool(token and len(token) > 10 and not is_expired)

    return {
        "ok": True,
        "is_logged_in": is_logged_in,
        "is_expired": is_expired,
        "user_name": prof.get("user_name", "长龙会员"),
        "mobile": masked_mobile,
        "raw_mobile": mobile,
        "cert_number": masked_cert,
        "member_level": prof.get("member_level", "乘云会员"),
        "card_name": prof.get("card_name", "长龙畅飞卡"),
        "is_verified": prof.get("is_verified", 0),
        "update_time": update_time,
        "auth_preview": auth_preview
    }

def reset_user_auth() -> dict:
    clear_auth_expired()
    db.save_user_profile({
        "user_name": "长龙会员",
        "mobile": "",
        "member_level": "普通会员",
        "cert_number": "",
        "token": "",
        "cookie": "",
        "card_name": "长龙畅飞卡",
        "encrypted_user_id": "",
        "sec_card_grant_tid": "",
        "coupons_count": 0,
        "cards_count": 0,
        "points": 0,
        "is_verified": 0,
        "headers_json": "{}",
        "template_json": "{}",
        "updated_at": ""
    })
    return {"ok": True, "message": "已成功清空本地会员凭证，已恢复初始状态"}


# 初始化本地 SQLite 数据库
db.init_db()

PORT = 3000
APP_VERSION = "v2.1.2"
GITHUB_REPO = "eureka-wu/clairline"
client = SecCardClient()
scheduler = MonitorScheduler(client)

def check_github_update():
    """向 GitHub Releases API 检索最新版本与发布日志 (方案 A)"""
    import urllib.request, re
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Clairline-Desktop",
            "Accept": "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "").strip()

            def parse_ver(v_str):
                nums = re.findall(r"\d+", v_str)
                return [int(x) for x in nums] if nums else [0]

            curr_v = parse_ver(APP_VERSION)
            latest_v = parse_ver(latest_tag)
            has_update = latest_v > curr_v

            # 寻找发布的 exe 附件直接下载链接
            download_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe"):
                    download_url = asset.get("browser_download_url", download_url)
                    break

            return {
                "ok": True,
                "current_version": APP_VERSION,
                "latest_version": latest_tag or APP_VERSION,
                "has_update": has_update,
                "release_name": data.get("name", latest_tag),
                "release_notes": data.get("body", ""),
                "page_url": data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
                "download_url": download_url
            }
    except Exception as ex:
        err_msg = str(ex)
        # 核心防空处理：若 GitHub 仓库尚未正式发布 Release，GitHub API 会返回 404 Not Found
        # 此时应判定为正常状态，当前即为最新版，绝不向用户弹报错 Toast
        if "404" in err_msg or "Not Found" in err_msg:
            return {
                "ok": True,
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "has_update": False,
                "release_name": "长龙航空畅飞助手 v2.0",
                "release_notes": "当前已是官方最新版本，暂无新版本发布。",
                "page_url": f"https://github.com/{GITHUB_REPO}/releases",
                "download_url": f"https://github.com/{GITHUB_REPO}/releases"
            }
        return {
            "ok": False,
            "current_version": APP_VERSION,
            "latest_version": APP_VERSION,
            "has_update": False,
            "error": err_msg,
            "page_url": f"https://github.com/{GITHUB_REPO}/releases"
        }


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
            if sys.stdout and hasattr(sys.stdout, "flush"):
                try: sys.stdout.flush()
                except Exception: pass

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
        if sys.stdout and hasattr(sys.stdout, "write"):
            try:
                sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
                if hasattr(sys.stdout, "flush"):
                    sys.stdout.flush()
            except Exception:
                pass

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
                    client.check_and_reload()
                if not client.headers:
                    self.send_json({"ok": False, "error": "当前未登录或缺少会员凭据，请先在右上角使用【手机验证码登录】！"}, 401)
                    return
                try:
                    cal = client.get_calendar(from_code, to_code)
                    db.save_route_calendar(frm, to, cal)
                except Exception as ex:
                    err_msg = str(ex)
                    if "100001" in err_msg or "403" in err_msg or "未登录" in err_msg or "未登入" in err_msg:
                        mark_auth_expired()
                        self.send_json({"ok": False, "error": "长龙会员登录凭据已过期 (100001)，请在右上角使用【手机验证码登录】重新续期", "authExpired": True}, 401)
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
            # 从 SQLite 数据库读取重点巡检航线详细配置 (含名称，不设上限)
            routes = db.get_patrol_routes_detailed()
            cfg = db.get_patrol_config()
            interval = int(cfg.get("hot_interval_minutes", "25"))
            self.send_json({"ok": True, "routes": routes, "count": len(routes), "interval": interval})
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

        elif path == "/api/auth/status":
            self.send_json(get_auth_status())
            return

        elif path == "/api/system/check-update":
            update_info = check_github_update()
            self.send_json(update_info)
            return

        elif path == "/api/system/info":
            self.send_json({
                "ok": True,
                "version": APP_VERSION,
                "github": f"https://github.com/{GITHUB_REPO}",
                "repo": GITHUB_REPO,
                "mcp": {
                    "enabled": True,
                    "sse_endpoint": "/sse",
                    "rpc_endpoint": "/api/mcp/rpc"
                }
            })
            return

        elif path in ("/sse", "/api/mcp/sse"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                self.wfile.write(b"event: endpoint\ndata: /api/mcp/rpc\n\n")
                self.wfile.flush()
            except Exception:
                pass
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
            interval = body.get("interval")
            if interval:
                try:
                    db.update_patrol_config({"hot_interval_minutes": str(int(interval))})
                except Exception:
                    pass
            # 持久化写入 SQLite 数据库 (不设上限，支持每条航线名称)
            count = db.set_patrol_routes(routes)
            detailed = db.get_patrol_routes_detailed()
            self.send_json({"ok": True, "routes": detailed, "count": count})
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
            qs = urllib.parse.parse_qs(parsed.query)
            query_mode = qs.get("mode", [""])[0]
            mode = body.get("mode") or query_mode or "hot"
            if mode not in ["hot", "all"]:
                mode = "hot"
            if auto_patrol.PATROL_STATE.get("running"):
                current_mode = auto_patrol.PATROL_STATE.get("mode", "hot")
                self.send_json({
                    "ok": True, 
                    "already_running": True, 
                    "mode": current_mode,
                    "message": f"当前已有{'全网普查' if current_mode == 'all' else '热门巡检'}正在进行中，已自动连接实时进度！"
                }, 200)
                return
            
            # 100% 优先且唯一从 SQLite 数据库重载会员凭据与畅飞卡模板
            client.check_and_reload()
            if not client.headers:
                self.send_json({
                    "ok": False,
                    "error": "未检测到有效会员登录凭据，请先在右上角使用【手机验证码登录】！"
                }, 401)
                return

            # 启动前健康探针：同步检测登录态是否依然存活
            try:
                client.check_and_reload()
                client.get_calendar("杭州", "深圳")
            except Exception as auth_err:
                err_text = str(auth_err)
                if "100001" in err_text or "403" in err_text or "未登录" in err_text or "未登入" in err_text:
                    mark_auth_expired()
                    self.send_json({
                        "ok": False,
                        "error": "长龙会员登录凭据已失效，请在右上角使用【手机验证码登录】重新续期！",
                        "authExpired": True
                    }, 401)
                    return
                elif "scgtid" in err_text.lower() or not client.template.get("secCardGrantTid"):
                    self.send_json({
                        "ok": False,
                        "error": "已获取会员身份，但尚未获取到有效的长龙畅飞卡资产授权！"
                    }, 400)
                    return
                else:
                    self.send_json({"ok": False, "error": f"长龙接口提示: {err_text}"}, 400)
                    return

            auto_patrol.PATROL_STATE["running"] = True
            auto_patrol.PATROL_STATE["mode"] = mode
            auto_patrol.PATROL_STATE["total"] = len(auto_patrol.load_all_routes()) if mode == "all" else len(auto_patrol.load_hot_routes())
            auto_patrol.PATROL_STATE["completed"] = 0
            auto_patrol.PATROL_STATE["percent"] = 0
            auto_patrol.PATROL_STATE["status_text"] = "正在初始化巡检队列..."

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

        elif path == "/api/auth/reset":
            res = reset_user_auth()
            client.check_and_reload()
            self.send_json(res, 200 if res.get("ok") else 500)
            return

        elif path == "/api/auth/send-code":
            mobile = str(body.get("mobile") or "").strip()
            check_param = str(body.get("checkParam") or "").strip()
            from loongair_client import send_sms_verify_code
            res = send_sms_verify_code(mobile, check_param)
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        elif path == "/api/auth/login-code":
            mobile = str(body.get("mobile") or "").strip()
            code = str(body.get("code") or "").strip()
            verify_id = str(body.get("verifyId") or "").strip()
            from loongair_client import login_by_mobile_code
            res = login_by_mobile_code(mobile, code, verify_id)
            if res.get("ok"):
                clear_auth_expired()
                client.check_and_reload()
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        elif path in ("/api/mcp/rpc", "/mcp/rpc", "/rpc"):
            res = mcp_server.process_mcp_request(body)
            self.send_json(res if res is not None else {})
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

def start_session_keepalive_daemon():
    """后台守护线程：每 12 分钟向长龙网关发送一次轻量级保活心跳，防止服务端 Redis Session 因闲置超时被回收"""
    def _keepalive_loop():
        time.sleep(2)
        while True:
            try:
                from loongair_client import keepalive_session
                res = keepalive_session()
                if res.get("ok"):
                    clear_auth_expired()
                    client.check_and_reload()
                elif res.get("expired"):
                    mark_auth_expired()
            except Exception as e:
                print(f"[KeepAlive] 会话保活巡检提示: {e}")
            time.sleep(720)

    t = threading.Thread(target=_keepalive_loop, daemon=True, name="SessionKeepAlive")
    t.start()


def run():
    start_session_keepalive_daemon()
    host = os.environ.get("CLAIRLINE_HOST", "0.0.0.0")
    port = int(os.environ.get("CLAIRLINE_PORT", PORT))
    server = http.server.ThreadingHTTPServer((host, port), AppHandler)
    display_host = "localhost" if host == "0.0.0.0" else host
    print("\n=======================================================")
    print(f"✈️ 长龙航空畅飞卡前后端统一服务已启动！")
    print(f"🌐 本地 Web 访问: http://{display_host}:{port}")
    print(f"📡 实时 API 就绪: http://{display_host}:{port}/api/status")
    print(f"🤖 MCP 智能助手: http://{display_host}:{port}/sse (JSON-RPC: /api/mcp/rpc)")
    print(f"🛡️ 后台自动轮询: 已彻底关闭 (仅响应用户前端点击与按需查票)")
    print("=======================================================\n")
    if sys.stdout and hasattr(sys.stdout, "flush"):
        try:
            sys.stdout.flush()
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if scheduler.running:
            scheduler.stop()
        print("\n服务已平稳关闭。")

if __name__ == "__main__":
    run()
