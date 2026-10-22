#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出纯有票航线数据供纯静态前端秒级读取
======================================================
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
CALENDAR_FILE = BACKEND_DIR / "data" / "full_network_calendar.json"
FLIGHT_ROUTES_FILE = BACKEND_DIR / "data" / "flight-routes.json"
FRONTEND_DATA_DIR = PROJECT_DIR / "frontend" / "data"
FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = FRONTEND_DATA_DIR / "available_routes.json"

def main():
    if not CALENDAR_FILE.exists():
        print(f"Error: {CALENDAR_FILE} does not exist.")
        return

    # 1. 读取日历全量数据
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        cal_data = json.load(f)

    # 2. 读取基础航班信息以关联航班号、起飞降落时间
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
                    })
        except Exception as e:
            print(f"Warning: failed to load flight-routes.json: {e}")

    # 常见城市三字码映射
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

    calendar_dict = cal_data.get("calendarData", {})
    available_routes = []

    for route_key, item in calendar_dict.items():
        frm = item.get("from")
        to = item.get("to")
        cal = item.get("calendar", {})

        # 筛选出所有状态为 1 的可兑换日期
        avail_dates = [d for d, status in cal.items() if status == 1]
        
        # 只保留真正有票的航线！
        if not avail_dates:
            continue

        # 按日期升序排列
        avail_dates.sort()

        # 航班信息
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

    # 按可兑换天数降序排序，让最容易换票的航线排在最前
    available_routes.sort(key=lambda x: x["availableDaysCount"], reverse=True)

    result = {
        "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "totalScannedRoutes": len(calendar_dict),
        "totalAvailableRoutes": len(available_routes),
        "totalDatePoints": sum(r["availableDaysCount"] for r in available_routes),
        "routes": available_routes
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 导出为 JS 变量供无服务器本地双击打开直接可用
    js_file = PROJECT_DIR / "frontend" / "js" / "available-routes-data.js"
    with open(js_file, "w", encoding="utf-8") as f:
        f.write("window.AVAILABLE_ROUTES_DATA = " + json.dumps(result, ensure_ascii=False) + ";\n")

    # 同时也拷贝一份给 backend/data/ 以便后台也能查
    with open(BACKEND_DIR / "data" / "available_routes.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"成功导出 {len(available_routes)} 条有票航线至 {OUT_FILE} 与 {js_file}！")

if __name__ == "__main__":
    main()
