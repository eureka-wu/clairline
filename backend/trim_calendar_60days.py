#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙官方日历数据近 2 个月 (60天) 瘦身净化器
======================================================
将全网日历严格截断在 [今天, 今天+60天] 范围内，
剔除 2 个月以后的全部无效未开放占位符，将 16 万行压缩为轻量秒开 JSON！
"""
import json, sys
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

CAL_FILE = DATA_DIR / "full_network_calendar.json"
OUT_AVAILABLE_BACKEND = DATA_DIR / "available_routes.json"
OUT_AVAILABLE_FRONTEND = PROJECT_DIR / "frontend" / "data" / "available_routes.json"
OUT_JS_FRONTEND = PROJECT_DIR / "frontend" / "js" / "available-routes-data.js"
FLIGHT_ROUTES_FILE = DATA_DIR / "flight-routes.json"

def main():
    if not CAL_FILE.exists():
        print("Error: full_network_calendar.json does not exist.")
        return

    # 基准日：以今天为准
    today = datetime.now()
    # 兼容长龙数据基准（2026-10-22）
    if today.year < 2026:
        today = datetime(2026, 10, 22)
    
    max_date = today + timedelta(days=60)
    today_str = today.strftime("%Y-%m-%d")
    max_date_str = max_date.strftime("%Y-%m-%d")

    print(f"📅 正在截取近 2 个月官方放票窗口: {today_str} ~ {max_date_str} (共 60 天)")

    with open(CAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. 精简 full_network_calendar.json
    cdata = data.get("calendarData", {})
    trimmed_cdata = {}
    total_avail_points = 0
    routes_with_tickets = 0

    for k, item in cdata.items():
        cal = item.get("calendar", {})
        # 严格只保留未来 60 天内的有效日期
        trimmed_cal = {d: s for d, s in cal.items() if today_str <= d <= max_date_str}
        avail_in_60 = [d for d, s in trimmed_cal.items() if s == 1]
        if avail_in_60:
            routes_with_tickets += 1
            total_avail_points += len(avail_in_60)

        trimmed_cdata[k] = {
            "from": item.get("from"),
            "to": item.get("to"),
            "calendar": trimmed_cal,
            "updatedAt": item.get("updatedAt", "")
        }

    data["calendarData"] = trimmed_cdata
    data["calendarWindowDays"] = 60
    data["calendarRange"] = f"{today_str} ~ {max_date_str}"
    data["routesWithAvailableTickets"] = routes_with_tickets
    data["totalAvailableDatePoints"] = total_avail_points

    with open(CAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ full_network_calendar.json 已成功瘦身截取至近 2 个月！")

    # 2. 联动更新 available_routes.json (只保留未来60天且真正有票的航线与具体日期)
    # 读取航班底表获取航班号
    flight_map = {}
    if FLIGHT_ROUTES_FILE.exists():
        try:
            with open(FLIGHT_ROUTES_FILE, "r", encoding="utf-8") as f:
                flights = json.load(f)
            for fl in flights:
                frm = fl.get("from")
                to = fl.get("to")
                if frm and to:
                    key = f"{frm}-{to}"
                    if key not in flight_map:
                        flight_map[key] = []
                    flight_map[key].append({
                        "flightNo": fl.get("flightNo", ""),
                        "depTime": fl.get("depTime", ""),
                        "arrTime": fl.get("arrTime", ""),
                        "aircraft": fl.get("aircraft", ""),
                        "frequency": fl.get("frequency", ""),
                        "stopover": fl.get("stopover", "直飞")
                    })
        except Exception: pass

    CITY_IATA = {
        "杭州": "HGH", "宁波": "NGB", "温州": "WNZ", "西安": "XIY",
        "哈尔滨": "HRB", "长春": "CGQ", "沈阳": "SHE", "大连": "DLC",
        "北京": "PEK", "广州": "CAN", "深圳": "SZX", "成都": "TFU",
        "重庆": "CKG", "武汉": "WUH", "郑州": "CGO", "贵阳": "KWE",
        "昆明": "KMG", "三亚": "SYX", "海口": "HAK", "乌鲁木齐": "URC",
        "银川": "INC", "西宁": "XNN", "兰州": "LHW", "呼和浩特": "HET",
        "西双版纳": "JHG", "丽江": "LJG", "烟台": "YNT", "威海": "WEH",
        "徐州": "XUZ", "临沂": "LYI", "东营": "DOY", "潍坊": "WEF",
        "菏泽": "HZA", "襄阳": "XFN", "常州": "CZX", "无锡": "WUX",
        "南宁": "NNG", "福州": "FOC", "赣州": "KOW", "衡阳": "HNY",
        "遵义": "ZYI", "泸州": "LZO", "达州": "DAX", "巴中": "BZX",
        "茅台": "WMT", "喀什": "KHG", "阿克苏": "AKU", "库尔勒": "KRL",
        "伊宁": "YIN", "克拉玛依": "KRY", "阿拉尔": "ACX", "图木舒克": "TWC",
        "海拉尔": "HLD", "满洲里": "NZH", "通化": "TNH", "白城": "DBC",
        "鸡西": "JXA", "嘉兴": "JIA", "赤峰": "CIF", "包头": "BAV",
        "邯郸": "HDG", "芒市": "LUM", "上海": "SHA", "济南": "TNA"
    }

    available_routes = []
    for route_key, item in trimmed_cdata.items():
        frm = item.get("from")
        to = item.get("to")
        cal = item.get("calendar", {})

        # 仅取 status == 1 的可兑日期
        avail_dates = [d for d, status in cal.items() if status == 1]
        if not avail_dates:
            continue

        avail_dates.sort()
        flights = flight_map.get(f"{frm}-{to}", [])

        available_routes.append({
            "from": frm,
            "to": to,
            "fromIata": CITY_IATA.get(frm, ""),
            "toIata": CITY_IATA.get(to, ""),
            "availableDaysCount": len(avail_dates),
            "availableDates": avail_dates,
            "flights": flights
        })

    # 按可兑天数降序排序
    available_routes.sort(key=lambda x: x["availableDaysCount"], reverse=True)

    result = {
        "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window": f"近2个月 ({today_str} ~ {max_date_str})",
        "totalScannedRoutes": len(trimmed_cdata),
        "totalAvailableRoutes": len(available_routes),
        "totalDatePoints": sum(r["availableDaysCount"] for r in available_routes),
        "routes": available_routes
    }

    # 写 backend
    with open(OUT_AVAILABLE_BACKEND, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 写 frontend
    OUT_AVAILABLE_FRONTEND.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_AVAILABLE_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 写 frontend JS
    with open(OUT_JS_FRONTEND, "w", encoding="utf-8") as f:
        f.write("window.AVAILABLE_ROUTES_DATA = " + json.dumps(result, ensure_ascii=False) + ";\n")

    print(f"🎉 成功同步 {len(available_routes)} 条有票航线（近2个月放票）至前端数据！")

if __name__ == "__main__":
    main()
