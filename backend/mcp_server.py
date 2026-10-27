#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞智能助手 - Model Context Protocol (MCP) Server
支持以 stdio 管道或 HTTP/SSE 模式作为 AI 助手的工具集插件运行。
标准规范: JSON-RPC 2.0 / MCP Specification
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# 保证 backend 和根目录处于 import 搜索路径中
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
for p in [str(CURRENT_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import db
    from seccard_client import SecCardClient
except ImportError:
    from backend import db
    from backend.seccard_client import SecCardClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_server")

# 懒加载单例 Client
_client_instance = None
def get_client():
    global _client_instance
    if _client_instance is None:
        db.init_db()
        _client_instance = SecCardClient()
    return _client_instance

# ==========================================
# MCP 工具注册表 (Tool Definitions)
# ==========================================
MCP_TOOLS = [
    {
        "name": "query_flight_tickets",
        "description": "实时向长龙航空官方接口发起在线查票，获取指定航线在指定出发日期的航班号、机型、起降时刻与当前畅飞卡/免票真实剩余座位数。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_city": {
                    "type": "string",
                    "description": "出发城市中文名称或三字码，例如：'杭州'、'银川'、'HGH'"
                },
                "to_city": {
                    "type": "string",
                    "description": "到达目的地城市中文名称或三字码，例如：'阿勒泰'、'西双版纳'、'AAT'"
                },
                "date": {
                    "type": "string",
                    "description": "出发日期，格式为 YYYY-MM-DD，例如：'2026-10-30'"
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "是否强制穿透实时查询长龙官方接口（默认 true；若为 false 则优先读取本地最近查验缓存）",
                    "default": True
                }
            },
            "required": ["from_city", "to_city", "date"]
        }
    },
    {
        "name": "get_route_calendar",
        "description": "从本地 SQLite 数据库中检索指定航线未来 60 天内的放票日历概览，快速查看哪些日期有票可兑换、余票数量及最后查验时间。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_city": {
                    "type": "string",
                    "description": "出发城市，例如：'杭州'"
                },
                "to_city": {
                    "type": "string",
                    "description": "到达城市，例如：'西双版纳'"
                }
            },
            "required": ["from_city", "to_city"]
        }
    },
    {
        "name": "get_direct_destinations",
        "description": "查询长龙航空航网拓扑中从指定出发地直飞可达的所有目的地城市列表（全国 397 条直飞网络），附带所属省份与航网规模。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_city": {
                    "type": "string",
                    "description": "出发城市，例如：'杭州'、'宁波'、'温州'、'西安'，默认 '杭州'",
                    "default": "杭州"
                }
            }
        }
    },
    {
        "name": "list_patrol_monitors",
        "description": "查询当前后台重点监控轮巡航线列表，获取正在被系统自动监控放票的航线与自定义备注标签。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_patrol_monitor",
        "description": "将一条航线添加到后台重点监控列表中，后台巡检服务将自动在轮巡中对该航线进行放票监控与日历更新。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_city": {
                    "type": "string",
                    "description": "出发城市，例如：'杭州'"
                },
                "to_city": {
                    "type": "string",
                    "description": "到达城市，例如：'阿勒泰'"
                },
                "remark": {
                    "type": "string",
                    "description": "自定义备注标签（选填），例如：'五一滑雪度假' 或 '回家探亲'"
                }
            },
            "required": ["from_city", "to_city"]
        }
    },
    {
        "name": "get_user_profile",
        "description": "获取当前在长龙助手登录的会员信息，包括乘云会员级别、真实姓名、畅飞卡产品及绑定状态。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# ==========================================
# 工具具体执行逻辑 (Tool Handlers)
# ==========================================
def handle_query_flight_tickets(arguments: dict) -> dict:
    from_city = arguments.get("from_city", "").strip()
    to_city = arguments.get("to_city", "").strip()
    date_str = arguments.get("date", "").strip()
    force_refresh = arguments.get("force_refresh", True)

    if not from_city or not to_city:
        return {"error": "缺少出发地 (from_city) 或目的地 (to_city)"}
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    frm = db.normalize_city(from_city)
    to = db.normalize_city(to_city)
    from_code = db.normalize_iata(from_city)
    to_code = db.normalize_iata(to_city)

    client = get_client()

    # 1. 如果不强制刷新，先看本地缓存
    if not force_refresh:
        try:
            cached = db.get_saved_flight_details(frm, to, date_str)
            if cached:
                return {
                    "from": frm,
                    "to": to,
                    "date": date_str,
                    "source": "local_cache",
                    "flight_count": len(cached),
                    "flights": cached
                }
        except Exception:
            pass

    # 2. 直连长龙官方接口实时查验
    try:
        flights = client.search_flights(from_code, to_code, date_str)
        try:
            db.save_seat_query_result(frm, to, date_str, flights)
        except Exception as e:
            logger.warning(f"查票结果落库异常: {e}")

        # 格式化提炼数据，方便大模型阅读
        cleaned_flights = []
        for f in flights:
            cleaned_flights.append({
                "flight_no": f.get("flight_no") or f.get("flightNo") or "长龙航班",
                "dep_time": f.get("dep_time") or f.get("departureTime"),
                "arr_time": f.get("arr_time") or f.get("arriveTime"),
                "aircraft": f.get("aircraft") or f.get("aircraftType", "A320"),
                "stopover": f.get("stopover", "直飞"),
                "remain_seats": f.get("remain_seats", 0),
                "is_available": (f.get("remain_seats", 0) > 0)
            })

        return {
            "from": frm,
            "to": to,
            "date": date_str,
            "source": "loongair_live",
            "flight_count": len(cleaned_flights),
            "flights": cleaned_flights,
            "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as ex:
        # 降级尝试返回本地记录
        try:
            cached = db.get_saved_flight_details(frm, to, date_str)
            if cached:
                return {
                    "from": frm,
                    "to": to,
                    "date": date_str,
                    "source": "fallback_cache",
                    "warning": f"实时接口提示: {ex}，已为您降级提供本地查验记录",
                    "flights": cached
                }
        except Exception:
            pass
        return {"error": f"长龙实时查票失败: {str(ex)}"}

def handle_get_route_calendar(arguments: dict) -> dict:
    from_city = db.normalize_city(arguments.get("from_city", "").strip())
    to_city = db.normalize_city(arguments.get("to_city", "").strip())
    if not from_city or not to_city:
        return {"error": "缺少出发城市 (from_city) 或到达城市 (to_city)"}

    db.init_db()
    # 严格读取在起兑日之后且有放票的有效出行日
    available_dates = db.get_available_dates(from_city, to_city)
    seat_queries = db.get_seat_queries_for_route(from_city, to_city)

    date_details = []
    for d in available_dates:
        sq = seat_queries.get(d)
        date_details.append({
            "flight_date": d,
            "has_ticket": True,
            "sec_card_remain": sq["count"] if sq else "有票(待点查具体座数)",
            "last_check_label": sq["timeLabel"] if sq else "日历同步",
            "last_check_time": sq["queryTime"] if sq else ""
        })

    return {
        "from": from_city,
        "to": to_city,
        "available_days_count": len(available_dates),
        "available_dates": date_details,
        "earliest_bookable_date": db.get_min_bookable_date(),
        "summary": f"{from_city} ➔ {to_city} 监测到未来共 {len(available_dates)} 天有票可兑"
    }

def handle_get_direct_destinations(arguments: dict) -> dict:
    from_city = db.normalize_city(arguments.get("from_city", "杭州").strip() or "杭州")
    db.init_db()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT to_city FROM flight_routes WHERE from_city = ? ORDER BY to_city ASC
    """, (from_city,))
    rows = cur.fetchall()
    conn.close()

    dests = [r["to_city"] for r in rows]
    return {
        "from_city": from_city,
        "direct_destination_count": len(dests),
        "destinations": dests
    }

def handle_list_patrol_monitors(arguments: dict) -> dict:
    db.init_db()
    routes = db.get_patrol_routes_detailed()
    cfg = db.get_patrol_config()
    interval = int(cfg.get("hot_interval_minutes", "25"))
    switches = db.get_patrol_switches()

    return {
        "monitored_routes_count": len(routes),
        "routes": routes,
        "patrol_interval_minutes": interval,
        "hot_patrol_enabled": switches.get("hot_enabled", False),
        "all_patrol_enabled": switches.get("all_enabled", False)
    }

def handle_add_patrol_monitor(arguments: dict) -> dict:
    from_city = db.normalize_city(arguments.get("from_city", "").strip())
    to_city = db.normalize_city(arguments.get("to_city", "").strip())
    remark = arguments.get("remark", "").strip() or f"{from_city} ➔ {to_city}"

    if not from_city or not to_city:
        return {"error": "缺少出发城市 (from_city) 或到达城市 (to_city)"}

    db.init_db()
    routes = db.get_patrol_routes_detailed()
    exists = any(r.get("from") == from_city and r.get("to") == to_city for r in routes)
    if not exists:
        routes.append({"from": from_city, "to": to_city, "name": remark})
        db.set_patrol_routes(routes)

    return {
        "ok": True,
        "message": f"成功将航线 {from_city} ➔ {to_city} 添加至重点监控巡检队列",
        "already_exists": exists,
        "total_monitored_routes": len(routes),
        "remark": remark
    }

def handle_get_user_profile(arguments: dict) -> dict:
    db.init_db()
    prof = db.get_user_profile()
    if not prof or not prof.get("token"):
        return {
            "logged_in": False,
            "message": "当前未登录长龙会员账号。请在长龙助手 Web 界面右上角输入手机号短信验证码完成绑定。"
        }

    mobile = prof.get("mobile", "")
    masked_mobile = f"{mobile[:3]}****{mobile[-4:]}" if len(mobile) == 11 else (mobile or "")
    cert = prof.get("cert_number", "")
    masked_cert = f"{cert[:6]}********{cert[-4:]}" if len(cert) > 10 else (cert or "")

    return {
        "logged_in": True,
        "user_name": prof.get("user_name", "长龙会员"),
        "mobile": masked_mobile,
        "cert_number": masked_cert,
        "member_level": prof.get("member_level", "普通会员"),
        "card_name": prof.get("card_name", "长龙畅飞卡"),
        "coupons_count": prof.get("coupons_count", 0),
        "cards_count": prof.get("cards_count", 0),
        "points": prof.get("points", 0),
        "is_verified": bool(prof.get("is_verified", 0)),
        "has_token": bool(prof.get("token")),
        "update_time": prof.get("updated_at", "")
    }

# 派发器字典
TOOL_DISPATCHER = {
    "query_flight_tickets": handle_query_flight_tickets,
    "get_route_calendar": handle_get_route_calendar,
    "get_direct_destinations": handle_get_direct_destinations,
    "list_patrol_monitors": handle_list_patrol_monitors,
    "add_patrol_monitor": handle_add_patrol_monitor,
    "get_user_profile": handle_get_user_profile,
}

# ==========================================
# JSON-RPC 2.0 / MCP 协议处理核心
# ==========================================
def process_mcp_request(req: dict) -> dict:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    # 1. 初始化握手
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "clairline-mcp",
                    "version": "2.1.1"
                }
            }
        }

    # 2. 查询支持的工具列表
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    # 3. 执行工具调用
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        handler = TOOL_DISPATCHER.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"未找到对应工具: {tool_name}"
                }
            }

        try:
            res_obj = handler(tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res_obj, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"执行工具异常: {str(e)}"
                        }
                    ]
                }
            }

    # 4. 心跳保活与通知响应
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    elif method and method.startswith("notifications/"):
        return None

    # 未知方法
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"未知 MCP 方法: {method}"
        }
    }

# ==========================================
# 模式 A: stdio 管道运行模式 (CLI / Docker exec)
# ==========================================
def run_stdio():
    logger.info("启动 Clairline MCP Server (stdio 管道模式)...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req = json.loads(line)
            resp = process_mcp_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.error(f"stdio 请求处理异常: {e}")

if __name__ == "__main__":
    run_stdio()
