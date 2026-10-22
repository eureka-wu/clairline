#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡接口核心客户端模块
封装对 https://www.loongair.cn/webhandler.ashx 的调用
包含：余量查询、45天日历查询、官方可达航线反查
"""
from __future__ import annotations
import gzip, json, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote
import zipfile

API = "https://www.loongair.cn/webhandler.ashx"
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

CITY_IATA = {
 '阿勒泰':'AAT','阿拉尔':'ACF','阿克苏':'AKU','巴中':'BZX','广州':'CAN','郑州':'CGO',
 '长春':'CGQ','重庆':'CKG','长沙':'CSX','成都':'CTU','大连':'DLC','东营':'DOY',
 '张家界':'DYG','达州':'DZH','恩施':'ENH','海口':'HAK','邯郸':'HDG','呼和浩特':'HET',
 '杭州':'HGH','海拉尔':'HLD','衡阳':'HNY','哈尔滨':'HRB','菏泽':'HZA','银川':'INC',
 '西双版纳':'JHG','泉州':'JJN','嘉兴':'JNH','鸡西':'JXA','喀什':'KHG','昆明':'KMG',
 '赣州':'KOW','克拉玛依':'KRY','贵阳':'KWE','兰州':'LHW','丽江':'LJG','芒市':'LUM',
 '临沂':'LYI','泸州':'LZO','宁波':'NGB','北京':'PEK','上海':'PVG','沈阳':'SHE',
 '荆州':'SHS','三亚':'SYX','深圳':'SZX','青岛':'TAO','通化':'TNH','图木舒克':'TWC',
 '太原':'TYN','乌鲁木齐':'URC','潍坊':'WEF','威海':'WEH','茅台':'WMT','温州':'WNZ',
 '武汉':'WUH','无锡':'WUX','襄阳':'XFN','西安':'XIY','西宁':'XNN','徐州':'XUZ',
 '烟台':'YNT','珠海':'ZUH','遵义':'ZYI','包头':'BAV','南京':'NKG','南宁':'NNG',
 '常州':'CZX','柳州':'LZH','济南':'TNA','福州':'FOC','赤峰':'CIF',
}
IATA_CITY = {v: k for k, v in CITY_IATA.items()}

def _split(raw: bytes):
    p = raw.split(b"\r\n\r\n", 1)
    return p[0].decode("utf-8", "replace"), (p[1] if len(p) > 1 else b"")

def _dechunk(b: bytes) -> bytes:
    out = bytearray(); i = 0
    while True:
        j = b.find(b"\r\n", i)
        if j < 0: break
        try: size = int(b[i:j].split(b";")[0].strip(), 16)
        except Exception: break
        if size == 0: break
        out += b[j+2:j+2+size]; i = j+2+size+2
    return bytes(out)

def _resp_json_from(raw: bytes):
    head, b = _split(raw)
    if "chunked" in head.lower(): b = _dechunk(b)
    if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
    return json.loads(b.decode("utf-8", "replace"))

class SecCardClient:
    def __init__(self, saz_path: Path | None = None):
        if saz_path is None:
            # 自动探测 saz 路径 (优先 cl.saz，兼容 changlong.saz)
            candidates = [
                BACKEND_DIR / "data" / "cl.saz",
                BACKEND_DIR / "data" / "changlong.saz",
                PROJECT_DIR / "cl.saz",
                PROJECT_DIR / "changlong.saz",
                Path.home() / "Desktop" / "cl.saz",
                Path.home() / "Desktop" / "changlong.saz"
            ]
            for c in candidates:
                if c.exists():
                    saz_path = c
                    break
        self.saz_path = saz_path
        self.headers: dict = {}
        self.template: dict = {}
        self.demo: dict = {}
        self.load_credentials()

    def load_credentials(self):
        if not self.saz_path or not self.saz_path.exists():
            print("⚠️ 未找到 cl.saz 或 changlong.saz 文件，请将抓包文件放入 backend/data/ 目录下")
            return
        z = zipfile.ZipFile(self.saz_path)
        names = sorted(n for n in z.namelist() if n.endswith("_c.txt"))
        headers = params = None
        for n in names:
            raw = z.read(n)
            head, body = _split(raw)
            if "webhandler" not in head.split("\r\n")[0]: continue
            btxt = body.decode("utf-8", "replace")
            if not btxt.startswith("paras="): continue
            try: pj = json.loads(unquote(btxt[len("paras="):]))
            except Exception: continue
            method = pj.get("MethodName", "")
            sname = n.replace("_c.txt", "_s.txt")
            if method == "secCardSearchFlights" and headers is None:
                headers = {}
                for ln in head.split("\r\n")[1:]:
                    if ":" in ln:
                        k, v = ln.split(":", 1); headers[k.strip()] = v.strip()
                params = json.loads(pj["Parameters"])
                if sname in z.namelist(): self.demo["flights"] = _resp_json_from(z.read(sname))
            if method == "getSecCardRedeemedCalendar" and "calendar" not in self.demo and sname in z.namelist():
                try: self.demo["calendar"] = _resp_json_from(z.read(sname))
                except Exception: pass
        if headers and params:
            # 关键：必须保留 Accept-Encoding，长龙 WAF 靠此识别合法请求，并在响应时 gzip 解压
            keep = ("Authorization", "NESign", "Cookie", "X-App-Version", "User-Agent", "Referer", "xweb_xhr", "Accept", "Accept-Encoding", "Accept-Language")
            self.headers = {k: headers[k] for k in keep if k in headers}
            self.template = params

    def call_api(self, method: str, params: dict):
        if not self.headers:
            raise RuntimeError("登录态未就绪：请确保 backend/data/cl.saz 或 changlong.saz 存在并有效")
        body_obj = {
            "AppID": "ClientService",
            "MethodName": method,
            "Parameters": json.dumps(params, ensure_ascii=False)
        }
        data = ("paras=" + quote(json.dumps(body_obj, ensure_ascii=False))).encode("utf-8")
        h = dict(self.headers)
        h["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        req = urllib.request.Request(API, data=data, headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw_bytes = r.read()
                if raw_bytes[:2] == b"\x1f\x8b":
                    raw_bytes = gzip.decompress(raw_bytes)
                payload = json.loads(raw_bytes.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise RuntimeError("长龙接口 403 Forbidden：Session 已失效或请求被拦截，请重新在小程序抓包覆盖 saz")
            raise RuntimeError(f"长龙接口 HTTP 错误: {e.code}")
        except Exception as e:
            raise RuntimeError(f"网络请求失败: {e}")

        if payload.get("ErrorCode") != 0:
            raise RuntimeError(f"长龙接口错误 ({payload.get('ErrorCode')}): {payload.get('message')}")
        res_str = payload.get("Result", "{}")
        return json.loads(res_str) if isinstance(res_str, str) else res_str

    def load_routes_index(self, frm_code: str, to_code: str) -> dict:
        """从 flight-routes.json 索引真实航班号"""
        candidates = [
            BACKEND_DIR / "data" / "flight-routes.json",
            PROJECT_DIR / "backend" / "data" / "flight-routes.json",
            PROJECT_DIR / "data" / "flight-routes.json",
            PROJECT_DIR / "flight-routes.json"
        ]
        rows = []
        for p in candidates:
            if p.exists():
                try:
                    rows = json.loads(p.read_text(encoding="utf-8"))
                    break
                except Exception: pass
        idx = {}
        fc, tc = IATA_CITY.get(frm_code, frm_code), IATA_CITY.get(to_code, to_code)
        for r in rows:
            if r.get("from") == fc and r.get("to") == tc and r.get("flightNo"):
                idx[(r["depTime"], r["arrTime"][:5])] = r["flightNo"]
        return idx

    def search_flights(self, frm: str, to: str, date_str: str) -> list[dict]:
        """查询某航线某日航班与真实余量"""
        frm_code = CITY_IATA.get(frm, frm)
        to_code = CITY_IATA.get(to, to)
        p = dict(self.template)
        p["departureAirportCode"] = frm_code
        p["arriveAirportCode"] = to_code
        p["departureTime"] = f"{date_str}T00:00:00"
        
        res = self.call_api("secCardSearchFlights", p)
        routes_idx = self.load_routes_index(frm_code, to_code)
        
        flight_items = []
        for fi in res.get("flightInfos", []):
            dep = fi["departureTime"][11:16]
            arr = fi["arriveTime"][11:16]
            f_no = routes_idx.get((dep, arr), f"{dep}班")
            for c in fi.get("cabinInfos") or []:
                flight_items.append({
                    "flightNo": f_no,
                    "depTime": dep,
                    "arrTime": arr,
                    "aircraft": fi.get("aircraftType", "A320"),
                    "redeemPrice": c.get("ticketPrice", 266),
                    "secCardLeft": c.get("secCardBaseLeftCount", 0),
                    "normalLeft": c.get("leftCount", 0),
                    "cabinCode": c.get("cabinCode", "M")
                })
        return flight_items

    def get_calendar(self, frm: str, to: str) -> dict:
        """查询整条航线近 60 天官方兑换日历 (1=有可兑, 0=已兑完, -1=未开放, -2=不适用, -3=已截止, -4=无航班)"""
        frm_code = CITY_IATA.get(frm, frm)
        to_code = CITY_IATA.get(to, to)
        p = {
            "scgTid": str(self.template.get("secCardGrantTid", "")),
            "departureCode": frm_code,
            "arriveCode": to_code,
            "SaleChannel": 76,
            "saleChannel": 76,
            "language": "zh-cn"
        }
        res = self.call_api("getSecCardRedeemedCalendar", p)
        raw_map = res.get("calenderMap", {})

        # 严格只保留【查询当天 + 60 天】窗口，丢弃之后 300 多天的未开放占位符
        today = datetime.now()
        if today.year < 2026: today = datetime(2026, 10, 22)
        today_str = today.strftime("%Y-%m-%d")
        from datetime import timedelta
        max_date_str = (today + timedelta(days=60)).strftime("%Y-%m-%d")
        return {d: s for d, s in raw_map.items() if today_str <= d <= max_date_str}

    def get_official_destinations(self, frm: str) -> list[str]:
        """从长龙官方直接拉取某出发地允许兑换的官方目的地城市列表"""
        frm_code = CITY_IATA.get(frm, frm)
        p = {
            "scgTid": str(self.template.get("secCardGrantTid", "")),
            "fromCode": frm_code,
            "SaleChannel": 76,
            "saleChannel": 76,
            "language": "zh-cn"
        }
        res = self.call_api("/coupon/client/getSecCardArriveAirport", p)
        dom = res.get("domAirports", {})
        cities = set()
        for letter, airports in dom.items():
            for a in airports:
                c = a.get("cityName", "")
                if "成都" in c: c = "成都"
                elif "北京" in c: c = "北京"
                elif "遵义" in c: c = "遵义"
                cities.add(c)
        return sorted(cities)
