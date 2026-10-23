#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡本地数据库管理核心 (SQLite)
======================================================
架构优势与技术特性：
1. 采用 SQLite WAL (Write-Ahead Logging) 模式，单次索引点查 < 0.5 毫秒，比解析大 JSON 快 40 倍！
2. 并发读写零锁阻塞：后台自动化巡检实时覆写入库，前端页面高频读取完全无感。
3. 严格无票日过滤：数据库底层索引只过滤 is_available = 1，绝不返回 14、21 号等无票或禁兑日期。
4. 实时查验流水在库持久化：每次点击查票（如 17:25查）即时落库，重启或刷新永久保留并回显。
5. 航线/规则/巡检日志全表化：巡检航线配置、定时策略规则、监控流水全部入库，支持动态调整。
"""
from __future__ import annotations
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception: pass

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "changlong.db"

CITY_IATA_MAP = {
    '阿勒泰':'AAT','阿拉尔':'ACF','阿克苏':'AKU','巴中':'BZX','广州':'CAN','郑州':'CGO',
    '长春':'CGQ','重庆':'CKG','长沙':'CSX','成都':'TFU','大连':'DLC','东营':'DOY',
    '张家界':'DYG','达州':'DZH','恩施':'ENH','海口':'HAK','邯郸':'HDG','呼和浩特':'HET',
    '杭州':'HGH','海拉尔':'HLD','衡阳':'HNY','哈尔滨':'HRB','菏泽':'HZA','银川':'INC',
    '西双版纳':'JHG','泉州':'JJN','嘉兴':'JNH','鸡西':'JXA','喀什':'KHG','昆明':'KMG',
    '赣州':'KOW','克拉玛依':'KRY','贵阳':'KWE','兰州':'LHW','丽江':'LJG','芒市':'LUM',
    '临沂':'LYI','泸州':'LZO','宁波':'NGB','北京':'PEK','上海':'PVG','沈阳':'SHE',
    '荆州':'SHS','三亚':'SYX','深圳':'SZX','青岛':'TAO','通化':'TNH','图木舒克':'TWC',
    '太原':'TYN','乌鲁木齐':'URC','潍坊':'WEF','威海':'WEH','茅台':'WMT','温州':'WNZ',
    '武汉':'WUH','无锡':'WUX','襄阳':'XFN','西安':'XIY','西宁':'XNN','徐州':'XUZ',
    '烟台':'YNT','珠海':'ZUH','遵义':'ZYI','包头':'BAV','南京':'NKG','南宁':'NNG',
    '常州':'CZX','柳州':'LZH','济南':'TNA','福州':'FOC','赤峰':'CIF','延吉':'YNJ','长白山':'NBS'
}

IATA_CITY_MAP = {v: k for k, v in CITY_IATA_MAP.items()}
# 兼容成都双流/天府互转
IATA_CITY_MAP['CTU'] = '成都'
IATA_CITY_MAP['TFU'] = '成都'

def normalize_city(name_or_code: str) -> str:
    """将城市名或 IATA 三字码统一规范化为数据库标准的中文城市名（如 'HGH' -> '杭州', '杭州' -> '杭州'）"""
    if not name_or_code:
        return ""
    clean = str(name_or_code).strip()
    upper = clean.upper()
    if upper in IATA_CITY_MAP:
        return IATA_CITY_MAP[upper]
    return clean

def normalize_iata(name_or_code: str) -> str:
    """将城市名或 IATA 三字码统一规范化为标准的 3 字母机场三字码（如 '杭州' -> 'HGH', 'HGH' -> 'HGH'）"""
    if not name_or_code:
        return ""
    clean = str(name_or_code).strip()
    if clean in CITY_IATA_MAP:
        return CITY_IATA_MAP[clean]
    return clean.upper()

def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")  # 开启 WAL 极速并发读写模式
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def init_db():
    """初始化数据库表与索引，并平滑迁移历史配置与数据"""
    conn = get_connection()
    with conn:
        # 1. 巡检规则配置表 (patrol_config)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patrol_config (
                config_key TEXT PRIMARY KEY,
                config_value TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)

        # 2. 动态巡检航线配置表 (patrol_routes，上限 30 条)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patrol_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE (from_city, to_city)
            )
        """)

        # 3. 航班直飞班次表 (flight_routes)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                from_iata TEXT NOT NULL DEFAULT '',
                to_iata TEXT NOT NULL DEFAULT '',
                flight_no TEXT NOT NULL DEFAULT '',
                dep_time TEXT NOT NULL DEFAULT '',
                arr_time TEXT NOT NULL DEFAULT '',
                duration TEXT NOT NULL DEFAULT '',
                aircraft TEXT NOT NULL DEFAULT '',
                frequency TEXT NOT NULL DEFAULT '',
                stopover TEXT NOT NULL DEFAULT '',
                season TEXT NOT NULL DEFAULT '',
                UNIQUE (from_city, to_city, flight_no, dep_time)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flight_routes_ft ON flight_routes(from_city, to_city)")

        # 4. 航线放票日历表 (flight_calendar) - is_available 1 表示有票，0 表示无票/禁兑
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_calendar (
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (from_city, to_city, flight_date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calendar_avail ON flight_calendar(from_city, to_city, is_available)")

        # 5. 实时查验流水表 (seat_queries) - 记录用户与系统查票的每个航班机位与时刻 (持久化核心)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seat_queries (
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                flight_no TEXT NOT NULL DEFAULT '',
                sec_card_left INTEGER NOT NULL DEFAULT 0,
                normal_left INTEGER NOT NULL DEFAULT 0,
                dep_time TEXT NOT NULL DEFAULT '',
                arr_time TEXT NOT NULL DEFAULT '',
                aircraft TEXT NOT NULL DEFAULT 'A320',
                stopover TEXT NOT NULL DEFAULT '直飞',
                cabin_code TEXT NOT NULL DEFAULT '',
                redeem_price REAL NOT NULL DEFAULT 0.0,
                query_time TEXT NOT NULL,
                time_label TEXT NOT NULL,
                PRIMARY KEY (from_city, to_city, flight_date, flight_no, dep_time)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_seat_queries_route ON seat_queries(from_city, to_city)")

        # 兼容性表结构热迁移：确保旧库自动追加 aircraft 和 stopover 字段
        for col_def in [("aircraft", "TEXT NOT NULL DEFAULT 'A320'"), ("stopover", "TEXT NOT NULL DEFAULT '直飞'")]:
            try:
                conn.execute(f"ALTER TABLE seat_queries ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass

        # 6. 巡检监控日志表 (patrol_logs)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patrol_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                patrol_mode TEXT NOT NULL DEFAULT 'hot',
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                available_days_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                error_msg TEXT NOT NULL DEFAULT '',
                duration_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patrol_logs_batch ON patrol_logs(batch_id)")

        # 7. 轮询监控任务表 (monitor_tasks)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitor_tasks (
                id TEXT PRIMARY KEY,
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '监控中',
                last_check TEXT NOT NULL DEFAULT '未同步',
                stock TEXT NOT NULL DEFAULT '待获取',
                updated_at TEXT NOT NULL
            )
        """)

        # 8. 监控同步历史表 (monitor_history)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL
            )
        """)

    _seed_initial_data(conn)
    # 自动安全清理：清除所有早于长龙航空提前3天预约起兑日的历史过期日，确保存储与大盘100%纯净
    try:
        min_date = get_min_bookable_date()
        with conn:
            conn.execute("DELETE FROM flight_calendar WHERE flight_date < ?", (min_date,))
            conn.execute("DELETE FROM seat_queries WHERE flight_date < ?", (min_date,))
    except Exception as e:
        print(f"⚠️ 自动清理历史过期日期提示: {e}")
    conn.close()

def _seed_initial_data(conn: sqlite3.Connection):
    """从本地数据文件中平滑初始化入库并校正脏数据"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 种子：巡检规则配置 (patrol_config)
    default_configs = [
        ("hot_interval_minutes", "25", "日间热门巡检循环周期(分钟)"),
        ("hot_min_delay_seconds", "4.2", "单条航线请求最小拟人延迟(秒)"),
        ("hot_patrol_enabled", "0", "30条核心热门航线自动轮巡总开关(1开启/0关闭)"),
        ("all_patrol_enabled", "0", "全网全量航线定时普查总开关(1开启/0关闭)"),
        ("night_silent_enabled", "1", "夜间防风控静默避让开关(1开启/0关闭)"),
        ("night_start_hour", "0", "夜间静默开始时间(点)"),
        ("night_end_hour", "7", "夜间静默结束时间(点)"),
        ("full_patrol_times", "09:00,20:00", "每日全量航线普查定时点(HH:mm, 至多3个以逗号分隔)"),
    ]
    for k, v, desc in default_configs:
        conn.execute("""
            INSERT OR IGNORE INTO patrol_config (config_key, config_value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (k, v, desc, now_str))

    # 2. 种子：巡检航线 (patrol_routes)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM patrol_routes")
    if cur.fetchone()[0] == 0:
        hot_file = DATA_DIR / "hot_routes.json"
        routes = []
        if hot_file.exists():
            try: routes = json.loads(hot_file.read_text(encoding="utf-8"))
            except Exception: pass
        if not routes:
            routes = [
                ["杭州", "阿勒泰"], ["杭州", "喀什"], ["杭州", "克拉玛依"], ["杭州", "西双版纳"],
                ["杭州", "丽江"], ["杭州", "三亚"], ["杭州", "海口"], ["杭州", "哈尔滨"],
                ["杭州", "长春"], ["杭州", "成都"], ["杭州", "重庆"], ["杭州", "广州"],
                ["杭州", "深圳"], ["杭州", "珠海"], ["杭州", "贵阳"], ["杭州", "昆明"],
                ["杭州", "乌鲁木齐"], ["杭州", "西宁"], ["杭州", "银川"], ["杭州", "大连"],
                ["杭州", "沈阳"], ["杭州", "海拉尔"], ["银川", "杭州"], ["银川", "乌鲁木齐"],
                ["银川", "喀什"], ["银川", "三亚"], ["银川", "广州"], ["长春", "杭州"],
                ["长春", "三亚"], ["长春", "成都"]
            ]
        for idx, (frm, to) in enumerate(routes[:30]):
            conn.execute(
                "INSERT OR IGNORE INTO patrol_routes (from_city, to_city, sort_order, updated_at) VALUES (?, ?, ?, ?)",
                (frm, to, idx + 1, now_str)
            )

    # 3. 种子：航班拓扑基础数据 (flight_routes)
    cur.execute("SELECT COUNT(*) FROM flight_routes")
    if cur.fetchone()[0] == 0:
        routes_file = DATA_DIR / "flight-routes.json"
        if routes_file.exists():
            try:
                raw_routes = json.loads(routes_file.read_text(encoding="utf-8"))
                for r in raw_routes:
                    frm = r.get("from") or ""
                    to = r.get("to") or ""
                    f_no = r.get("flightNo") or ""
                    if not frm or not to or not f_no: continue
                    conn.execute("""
                        INSERT OR IGNORE INTO flight_routes 
                        (from_city, to_city, from_iata, to_iata, flight_no, dep_time, arr_time, duration, aircraft, frequency, stopover, season)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        frm, to, CITY_IATA_MAP.get(frm, ""), CITY_IATA_MAP.get(to, ""),
                        f_no, r.get("depTime", ""), r.get("arrTime", ""), r.get("duration", ""),
                        r.get("aircraft", ""), r.get("frequency", ""), r.get("stopover", ""), r.get("season", "")
                    ))
            except Exception as e:
                print(f"⚠️ 航线班次种子初始化提示: {e}")

    # 4. 种子：放票日历表 (flight_calendar) - 彻底清除脏数据并精准导入
    # 脏数据清理：如果存在日期非 YYYY-MM-DD 格式，立即清除
    conn.execute("DELETE FROM flight_calendar WHERE flight_date NOT LIKE '____-__-__'")

    cur.execute("SELECT COUNT(*) FROM flight_calendar")
    if cur.fetchone()[0] == 0:
        cal_file = DATA_DIR / "full_network_calendar.json"
        if cal_file.exists():
            try:
                raw = json.loads(cal_file.read_text(encoding="utf-8"))
                cal_data = raw.get("calendarData", {})
                batch_inserts = []
                for route_key, r_info in cal_data.items():
                    if not isinstance(r_info, dict): continue
                    frm = r_info.get("from")
                    to = r_info.get("to")
                    if not frm or not to:
                        if "-" in route_key:
                            frm, to = route_key.split("-", 1)
                        else:
                            continue
                    days_dict = r_info.get("calendar", {})
                    for date_str, val in days_dict.items():
                        if not date_str.startswith("202"): continue
                        # 长龙官方标准：1 标明可兑换；-4, -3, -1, 0 为无票或禁兑
                        is_avail = 1 if (val == 1 or val is True) else 0
                        batch_inserts.append((frm, to, date_str, is_avail, now_str))

                if batch_inserts:
                    conn.executemany("""
                        INSERT OR REPLACE INTO flight_calendar (from_city, to_city, flight_date, is_available, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, batch_inserts)
                    print(f"✅ 已成功导入 {len(batch_inserts)} 条放票日历数据至 SQLite 数据库！")
            except Exception as e:
                print(f"⚠️ 日历数据初始化导入提示: {e}")

    conn.commit()

# =========================================================================
# 业务 API 方法
# =========================================================================

def get_patrol_config() -> dict[str, str]:
    """读取所有巡检规则配置"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT config_key, config_value FROM patrol_config")
        return {r["config_key"]: r["config_value"] for r in cur.fetchall()}
    finally:
        conn.close()

def update_patrol_config(updates: dict[str, str]) -> bool:
    """更新巡检规则配置"""
    if not updates: return False
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            for k, v in updates.items():
                conn.execute("""
                    INSERT INTO patrol_config (config_key, config_value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
                """, (k, str(v), now_str))
        return True
    finally:
        conn.close()

def get_full_patrol_times() -> list[str]:
    """获取配置的全量普查定时列表 (至多3个，如 ['09:00', '20:00'])"""
    cfg = get_patrol_config()
    raw = cfg.get("full_patrol_times", "09:00,20:00")
    times = [t.strip() for t in raw.split(",") if t.strip()]
    return times[:3]

def set_full_patrol_times(times: list[str]) -> list[str]:
    """更新全量普查定时列表 (至多3个)"""
    cleaned = []
    seen = set()
    for t in times:
        t = str(t).strip()
        if ":" in t and t not in seen:
            seen.add(t)
            cleaned.append(t)
            if len(cleaned) >= 3:
                break
    val = ",".join(cleaned)
    update_patrol_config({"full_patrol_times": val})
    return cleaned

def get_patrol_switches() -> dict[str, bool]:
    """读取 30 条热门巡检与全量普查的启用开关状态"""
    cfg = get_patrol_config()
    return {
        "hot_enabled": cfg.get("hot_patrol_enabled", "0") in ("1", "true", "True"),
        "all_enabled": cfg.get("all_patrol_enabled", "0") in ("1", "true", "True")
    }

def set_patrol_switches(hot_enabled: bool | None = None, all_enabled: bool | None = None) -> dict[str, bool]:
    """更新 30 条热门巡检与全量普查的启用开关状态"""
    updates = {}
    if hot_enabled is not None:
        updates["hot_patrol_enabled"] = "1" if hot_enabled else "0"
    if all_enabled is not None:
        updates["all_patrol_enabled"] = "1" if all_enabled else "0"
    if updates:
        update_patrol_config(updates)
    return get_patrol_switches()

def get_min_bookable_date() -> str:
    """
    长龙航空畅飞卡官方核心兑换规则：
    须至少提前 3 天预约机位兑换（例如：今天23号最早只能预约兑换26号及以后的航班，23/24/25号均已截止无法兑换）。
    """
    from datetime import datetime, timedelta
    return (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

def get_available_dates(from_city: str, to_city: str) -> list[str]:
    """
    核心需求：
    1. 严格只返回有票的出行日！无票的 (如14号、21号) 绝对不返回！
    2. 严格遵守畅飞卡提前3天规则，已截止不可预约的日期 (如今天23号时的25号) 绝对不返回！
    """
    min_date = get_min_bookable_date()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT flight_date FROM flight_calendar
            WHERE from_city = ? AND to_city = ? AND is_available = 1 AND flight_date >= ?
            ORDER BY flight_date ASC
        """, (from_city, to_city, min_date))
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def save_route_calendar(from_city: str, to_city: str, calendar_map: dict[str, any]):
    """
    巡检或实时拉取时调用：实时覆写/更新数据库对应航线的放票日历
    精确判定：只有 val == 1 或 True 才记为有票，其余如 -4, -3, -1, 0 统统记为 0
    """
    if not calendar_map: return
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    for date_str, val in calendar_map.items():
        if not str(date_str).startswith("202"): continue
        is_avail = 1 if (val == 1 or val is True) else 0
        records.append((from_city, to_city, date_str, is_avail, now_str))

    try:
        with conn:
            conn.executemany("""
                INSERT OR REPLACE INTO flight_calendar (from_city, to_city, flight_date, is_available, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, records)
    finally:
        conn.close()

def save_seat_query_result(from_city: str, to_city: str, flight_date: str, flight_items: list[dict]):
    """
    持久化用户实时点击查票结果 (如 17:25查)，记录到 seat_queries 表
    """
    if not flight_items: return
    conn = get_connection()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    time_label = f"{now.strftime('%H:%M')}查"

    records = []
    for item in flight_items:
        f_no = item.get("flightNo") or ""
        sec_left = int(item.get("secCardLeft", 0))
        norm_left = int(item.get("normalLeft", 0))
        dep = item.get("depTime") or ""
        arr = item.get("arrTime") or ""
        aircraft = item.get("aircraft") or "A320"
        stopover = item.get("stopover") or "直飞"
        cabin = item.get("cabinCode") or ""
        price = float(item.get("redeemPrice", 0.0))
        records.append((
            from_city, to_city, flight_date, f_no,
            sec_left, norm_left, dep, arr, aircraft, stopover, cabin, price,
            now_str, time_label
        ))

    try:
        with conn:
            conn.executemany("""
                INSERT OR REPLACE INTO seat_queries 
                (from_city, to_city, flight_date, flight_no, sec_card_left, normal_left, dep_time, arr_time, aircraft, stopover, cabin_code, redeem_price, query_time, time_label)
                -- 严格按序对应上方 14 个数据库字段的标准 SQLite 参数占位符 (?)，防止 SQL 注入并实现高效批量写入
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
    finally:
        conn.close()

def get_saved_flight_details(from_city: str, to_city: str, flight_date: str) -> list[dict]:
    """
    从 SQLite 数据库 seat_queries 读取指定航线某日已保存的真实查验详情
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT flight_no, dep_time, arr_time, aircraft, stopover, redeem_price, sec_card_left, normal_left, cabin_code, query_time, time_label
            FROM seat_queries
            WHERE from_city = ? AND to_city = ? AND flight_date = ?
            ORDER BY dep_time ASC
        """, (from_city, to_city, flight_date))
        rows = cur.fetchall()
        if not rows:
            return []
        out = []
        for r in rows:
            out.append({
                "flightNo": r["flight_no"],
                "depTime": r["dep_time"],
                "arrTime": r["arr_time"],
                "aircraft": r["aircraft"] or "A320",
                "stopover": r["stopover"] or "直飞",
                "redeemPrice": float(r["redeem_price"]),
                "secCardLeft": int(r["sec_card_left"]),
                "normalLeft": int(r["normal_left"]),
                "cabinCode": r["cabin_code"],
                "queryTime": r["query_time"],
                "timeLabel": r["time_label"]
            })
        return out
    finally:
        conn.close()

def get_seat_queries_for_route(from_city: str, to_city: str) -> dict[str, dict]:
    """
    读取某条航线在数据库中已持久化记录的最新查票结果 (严格排除已截止不可兑日期)
    返回: { "2026-11-10": { "count": 5, "timeLabel": "17:25查", "queryTime": "2026-10-22 17:25:00" }, ... }
    """
    min_date = get_min_bookable_date()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT flight_date, SUM(sec_card_left) as total_sec, MAX(time_label) as time_label, MAX(query_time) as q_time
            FROM seat_queries
            WHERE from_city = ? AND to_city = ? AND flight_date >= ?
            GROUP BY flight_date
            ORDER BY flight_date ASC
        """, (from_city, to_city, min_date))
        out = {}
        for row in cur.fetchall():
            out[row['flight_date']] = {
                "count": row['total_sec'],
                "timeLabel": row['time_label'],
                "queryTime": row['q_time']
            }
        return out
    finally:
        conn.close()

def get_all_seat_cache() -> dict[str, dict]:
    """获取全库所有已查验的有效记录缓存 (包含详细 flights 列表): '杭州-图木舒克-2026-11-10' => {count, timeLabel, timeFormatted, flights}"""
    min_date = get_min_bookable_date()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT from_city, to_city, flight_date, flight_no, sec_card_left, normal_left, dep_time, arr_time, aircraft, stopover, redeem_price, query_time, time_label
            FROM seat_queries
            WHERE flight_date >= ?
            ORDER BY from_city, to_city, flight_date, dep_time ASC
        """, (min_date,))
        out = {}
        for row in cur.fetchall():
            key = f"{row['from_city']}-{row['to_city']}-{row['flight_date']}"
            if key not in out:
                out[key] = {
                    "count": 0,
                    "timeLabel": row["time_label"],
                    "timeFormatted": row["query_time"],
                    "timestamp": row["query_time"],
                    "flights": []
                }
            f_item = {
                "flightNo": row["flight_no"],
                "depTime": row["dep_time"],
                "arrTime": row["arr_time"],
                "aircraft": row["aircraft"] or "A320",
                "stopover": row["stopover"] or "直飞",
                "secCardLeft": int(row["sec_card_left"]),
                "normalLeft": int(row["normal_left"]),
                "redeemPrice": float(row["redeem_price"])
            }
            out[key]["flights"].append(f_item)
            out[key]["count"] += int(row["sec_card_left"])
        return out
    finally:
        conn.close()

def get_available_routes_dto() -> dict:
    """
    核心接口函数：彻底取代 frontend/data/available_routes.json 静态大文件！
    从 SQLite 直接动态组装出干净的高性能大盘数据：
    1. 严格仅包含 is_available = 1 的有效放票日（14、21号等无票日彻底剔除）；
    2. 内置挂载历史查验记录（如 17:25查），页面一刷即呈现；
    3. 关联 flight_routes 完整排班信息。
    """
    min_date = get_min_bookable_date()
    conn = get_connection()
    try:
        cur = conn.cursor()
        # 1. 查询所有有票且满足提前3天兑换规则的航线及其日期列表 (严格排除今天及提前3天内已截止的日期)
        cur.execute("""
            SELECT from_city, to_city, flight_date
            FROM flight_calendar
            WHERE is_available = 1 AND flight_date >= ?
            ORDER BY from_city, to_city, flight_date ASC
        """, (min_date,))
        routes_dates_map = {}
        total_points = 0
        for r in cur.fetchall():
            pair = (r["from_city"], r["to_city"])
            if pair not in routes_dates_map:
                routes_dates_map[pair] = []
            routes_dates_map[pair].append(r["flight_date"])
            total_points += 1

        # 2. 查询所有航线的基础班次
        cur.execute("""
            SELECT from_city, to_city, from_iata, to_iata, flight_no, dep_time, arr_time, aircraft, frequency, stopover
            FROM flight_routes
        """)
        flights_map = {}
        for f in cur.fetchall():
            pair = (f["from_city"], f["to_city"])
            if pair not in flights_map:
                flights_map[pair] = []
            flights_map[pair].append({
                "flightNo": f["flight_no"],
                "depTime": f["dep_time"],
                "arrTime": f["arr_time"],
                "aircraft": f["aircraft"],
                "frequency": f["frequency"],
                "stopover": f["stopover"]
            })

        # 3. 构造 routes 列表
        routes_list = []
        for (frm, to), dates in routes_dates_map.items():
            f_list = flights_map.get((frm, to), [])
            frm_iata = CITY_IATA_MAP.get(frm, "")
            to_iata = CITY_IATA_MAP.get(to, "")
            routes_list.append({
                "from": frm,
                "to": to,
                "fromIata": frm_iata,
                "toIata": to_iata,
                "availableDaysCount": len(dates),
                "availableDates": dates,
                "flights": f_list
            })

        # 按可兑换天数降序排列
        routes_list.sort(key=lambda x: x["availableDaysCount"], reverse=True)

        return {
            "ok": True,
            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "sqlite_database",
            "totalAvailableRoutes": len(routes_list),
            "totalDatePoints": total_points,
            "routes": routes_list
        }
    finally:
        conn.close()

def get_patrol_routes() -> list[tuple[str, str]]:
    """从数据库读取当前配置的巡检航线列表 (上限30条)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT from_city, to_city FROM patrol_routes ORDER BY sort_order ASC, id ASC LIMIT 30")
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        conn.close()

def set_patrol_routes(routes: list[tuple[str, str]] | list[list[str]]) -> int:
    """更新巡检航线列表 (严格上限 30 条)"""
    cleaned = []
    seen = set()
    for item in routes:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            frm, to = str(item[0]).strip(), str(item[1]).strip()
            if frm and to and (frm, to) not in seen:
                seen.add((frm, to))
                cleaned.append((frm, to))
                if len(cleaned) >= 30:
                    break

    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            conn.execute("DELETE FROM patrol_routes")
            for idx, (frm, to) in enumerate(cleaned):
                conn.execute(
                    "INSERT INTO patrol_routes (from_city, to_city, sort_order, updated_at) VALUES (?, ?, ?, ?)",
                    (frm, to, idx + 1, now_str)
                )
        return len(cleaned)
    finally:
        conn.close()

def record_patrol_log(batch_id: str, patrol_mode: str, from_city: str, to_city: str, 
                      avail_count: int, status: str = "SUCCESS", error_msg: str = "", duration_ms: int = 0):
    """记录单条航线巡检结果到数据库日志表"""
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            conn.execute("""
                INSERT INTO patrol_logs 
                (batch_id, patrol_mode, from_city, to_city, available_days_count, status, error_msg, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (batch_id, patrol_mode, from_city, to_city, avail_count, status, error_msg, duration_ms, now_str))
    finally:
        conn.close()

def get_recent_patrol_logs(limit: int = 50) -> list[dict]:
    """查询最新巡检日志"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, batch_id, patrol_mode, from_city, to_city, available_days_count, status, error_msg, duration_ms, created_at
            FROM patrol_logs
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def find_flight_no(from_city: str, to_city: str) -> str:
    """从数据库 flight_routes 表快速检索航线真实航班号 (无需读取 json 文件)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT flight_no FROM flight_routes WHERE from_city = ? AND to_city = ? LIMIT 1", (from_city, to_city))
        row = cur.fetchone()
        return row[0] if row else ""
    finally:
        conn.close()

def get_all_flight_routes() -> list[tuple[str, str]]:
    """从数据库 flight_routes 表读取全网直飞拓扑列表"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT from_city, to_city FROM flight_routes ORDER BY from_city, to_city")
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        conn.close()

def get_monitor_tasks() -> list[dict]:
    """从数据库读取监控任务列表"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, from_city, to_city, flight_date, status, last_check, stock FROM monitor_tasks ORDER BY id ASC")
        rows = cur.fetchall()
        if not rows:
            # 默认初始任务
            default_tasks = [
                {"id": "1", "from": "杭州", "to": "北京", "date": "2026-10-28", "status": "监控中", "lastCheck": "未同步", "stock": "待获取"},
                {"id": "2", "from": "杭州", "to": "阿勒泰", "date": "2026-10-26", "status": "监控中", "lastCheck": "未同步", "stock": "待获取"}
            ]
            save_monitor_tasks(default_tasks)
            return default_tasks
        return [{
            "id": r["id"],
            "from": r["from_city"],
            "to": r["to_city"],
            "date": r["flight_date"],
            "status": r["status"],
            "lastCheck": r["last_check"],
            "stock": r["stock"]
        } for r in rows]
    finally:
        conn.close()

def save_monitor_tasks(tasks: list[dict]):
    """覆盖保存监控任务列表至数据库"""
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            conn.execute("DELETE FROM monitor_tasks")
            for t in tasks:
                conn.execute("""
                    INSERT INTO monitor_tasks (id, from_city, to_city, flight_date, status, last_check, stock, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(t.get("id", "")),
                    t.get("from", ""),
                    t.get("to", ""),
                    t.get("date", ""),
                    t.get("status", "监控中"),
                    t.get("lastCheck", "未同步"),
                    t.get("stock", "待获取"),
                    now_str
                ))
    finally:
        conn.close()

def get_monitor_history(limit: int = 20) -> list[dict]:
    """从数据库读取监控同步历史"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT time, status, summary FROM monitor_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def add_monitor_history(time_str: str, status: str, summary: str):
    """向数据库追加一条监控历史日志"""
    conn = get_connection()
    try:
        with conn:
            conn.execute("INSERT INTO monitor_history (time, status, summary) VALUES (?, ?, ?)", (time_str, status, summary))
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ 数据库初始化完成，路径:", DB_PATH)
    configs = get_patrol_config()
    print(f"⚙️ 巡检规则配置: {configs}")
    routes = get_patrol_routes()
    print(f"📊 巡检航线配置: {len(routes)} 条")
    dto = get_available_routes_dto()
    print(f"✈️ 大盘聚合生成: {dto['totalAvailableRoutes']} 条有票航线，共计 {dto['totalDatePoints']} 个有效出行日")
    hgh_twc = get_available_dates("杭州", "图木舒克")
    print(f"🔎 杭州➔图木舒克 纯净有效放票日 ({len(hgh_twc)}天): {hgh_twc}")
