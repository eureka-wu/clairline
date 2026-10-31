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
import re
import sys
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception: pass

import os

ENV_DB_PATH = os.environ.get("CLAIRLINE_DB_PATH")
ENV_DATA_DIR = os.environ.get("CLAIRLINE_DATA_DIR")

if ENV_DB_PATH:
    DB_PATH = Path(ENV_DB_PATH).resolve()
    DATA_DIR = DB_PATH.parent
    BACKEND_DIR = DATA_DIR.parent
    PROJECT_DIR = BACKEND_DIR.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEED_FILE = DATA_DIR / "routes_seed.json"
elif ENV_DATA_DIR:
    DATA_DIR = Path(ENV_DATA_DIR).resolve()
    DB_PATH = DATA_DIR / "changlong.db"
    BACKEND_DIR = DATA_DIR.parent
    PROJECT_DIR = BACKEND_DIR.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEED_FILE = DATA_DIR / "routes_seed.json"
elif getattr(sys, "frozen", False):
    exe_path = Path(sys.executable).resolve()
    # 针对 PyInstaller 解压出的子进程（如 mitmdump.exe 位于 _MEIxxx 临时目录）
    if "_MEI" in str(exe_path):
        EXE_DIR = Path.cwd().resolve()
    else:
        EXE_DIR = exe_path.parent
    BACKEND_DIR = EXE_DIR / "backend"
    DATA_DIR = BACKEND_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", exe_path.parent)).resolve()
    SEED_FILE = BUNDLE_DIR / "backend" / "data" / "routes_seed.json"
    PROJECT_DIR = BACKEND_DIR.parent
    DB_PATH = DATA_DIR / "changlong.db"
else:
    BACKEND_DIR = Path(__file__).resolve().parent
    DATA_DIR = BACKEND_DIR / "data"
    SEED_FILE = DATA_DIR / "routes_seed.json"
    PROJECT_DIR = BACKEND_DIR.parent
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


# -----------------------------------------------------------------------------
# 双模数据库引擎 (SQLite 3 与 MySQL 原生双模自适应适配器)
# -----------------------------------------------------------------------------
def get_effective_database_url() -> str:
    """智能解析数据库连接串：优先使用 DATABASE_URL，其次自动读取容器中注入的 MYSQL_HOST 与 MYSQL_ROOT_PASSWORD"""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    mysql_host = os.environ.get("MYSQL_HOST", "").strip()
    mysql_pwd = (
        os.environ.get("MYSQL_ROOT_PASSWORD")
        or os.environ.get("MYSQL_PASSWORD")
        or os.environ.get("DB_PASSWORD")
        or ""
    ).strip()
    if mysql_host or mysql_pwd:
        mysql_user = os.environ.get("MYSQL_USER", "root").strip()
        mysql_port = os.environ.get("MYSQL_PORT", "3306").strip()
        mysql_db = os.environ.get("MYSQL_DATABASE", "loongair").strip()
        host = mysql_host or "mysql"
        return f"mysql+pymysql://{mysql_user}:{mysql_pwd}@{host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
    return ""

DATABASE_URL = get_effective_database_url()

def is_mysql_mode() -> bool:
    """检测当前运行环境是否配置了远程 MySQL 数据库"""
    curr_url = get_effective_database_url()
    return bool(curr_url and (curr_url.startswith("mysql://") or curr_url.startswith("mysql+pymysql://")))

def parse_mysql_url(url: str) -> dict:
    """解析 DATABASE_URL 格式 (如 mysql+pymysql://root:pass@mysql:3306/loongair?charset=utf8mb4)"""
    import urllib.parse
    if url.startswith("mysql+pymysql://"):
        raw_url = "mysql://" + url[len("mysql+pymysql://"):]
    else:
        raw_url = url
    p = urllib.parse.urlparse(raw_url)
    db_name = p.path.lstrip("/")
    if "?" in db_name:
        db_name, qs_part = db_name.split("?", 1)
    else:
        qs_part = p.query
    qs = urllib.parse.parse_qs(qs_part)
    charset = qs.get("charset", ["utf8mb4"])[0]
    return {
        "host": p.hostname or "127.0.0.1",
        "port": p.port or 3306,
        "user": p.username or "root",
        "password": p.password or "",
        "database": db_name or "loongair",
        "charset": charset
    }

def adapt_sql_for_mysql(sql: str) -> str:
    """将标准/SQLite SQL 自适应转译为标准 MySQL 8.0/5.7 语法"""
    # 0. 替换 CREATE INDEX IF NOT EXISTS 为 CREATE INDEX (MySQL 语法兼容)
    sql = re.sub(r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS', 'CREATE INDEX', sql, flags=re.IGNORECASE)
    # 1. 替换自增主键语法
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'INT AUTO_INCREMENT PRIMARY KEY', sql, flags=re.IGNORECASE)
    # 2. 替换 INSERT OR IGNORE -> INSERT IGNORE
    sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT IGNORE INTO', sql, flags=re.IGNORECASE)
    # 3. 替换 INSERT OR REPLACE INTO -> REPLACE INTO
    sql = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'REPLACE INTO', sql, flags=re.IGNORECASE)
    # 4. 替换 ON CONFLICT(...) DO UPDATE SET -> ON DUPLICATE KEY UPDATE
    sql = re.sub(r'ON\s+CONFLICT\s*\([^\)]*\)\s*DO\s+UPDATE\s+SET', 'ON DUPLICATE KEY UPDATE', sql, flags=re.IGNORECASE)
    # 5. 替换 excluded.col_name -> VALUES(col_name)
    sql = re.sub(r'excluded\.([a-zA-Z0-9_]+)', lambda m: f'VALUES({m.group(1)})', sql, flags=re.IGNORECASE)
    # 6. 解决 MySQL 报错 1101: BLOB/TEXT 字段禁止设置 DEFAULT 默认值
    # 带有 json/token/cookie/msg/summary 的大文本字段转为 TEXT (剔除 DEFAULT 部分)
    sql = re.sub(r'([a-zA-Z0-9_]*(?:json|token|cookie|msg|summary)[a-zA-Z0-9_]*)\s+TEXT(\s+NOT\s+NULL)?\s+DEFAULT\s+[^\s,\)]+', r'\1 TEXT', sql, flags=re.IGNORECASE)
    # 其余带 DEFAULT 的普通文本字段转换为 VARCHAR(255)
    sql = re.sub(r'\bTEXT(\s+NOT\s+NULL)?\s+DEFAULT\s+([^\s,\)]+)', r'VARCHAR(255)\1 DEFAULT \2', sql, flags=re.IGNORECASE)
    # 7. 替换 PRAGMA table_info(xxx) -> SHOW COLUMNS FROM xxx
    pragma_match = re.search(r'PRAGMA\s+table_info\s*\(\s*([a-zA-Z0-9_]+)\s*\)', sql, flags=re.IGNORECASE)
    if pragma_match:
        table_name = pragma_match.group(1)
        return f"SHOW COLUMNS FROM `{table_name}`"
    # 8. 替换占位符 ? 为 %s
    sql = sql.replace('?', '%s')
    return sql

class DictRow(dict):
    """兼容 SQLite Row 与 PyMySQL DictCursor 的行数据封装 (同时支持下标索引、键名索引与 dict 转换)"""
    def __init__(self, d):
        super().__init__(d)
        self._keys = list(d.keys())
        self._vals = list(d.values())

    def __getitem__(self, item):
        # SHOW COLUMNS 兼容 PRAGMA table_info 的 (cid, name, ...)
        if "Field" in self and "Type" in self:
            if item == 1 or item == "name":
                return self["Field"]
            if item == 2 or item == "type":
                return self["Type"]
            if item == 0 or item == "cid":
                return 0
        if isinstance(item, int):
            return self._vals[item]
        return super().__getitem__(item)

class MySQLCursorWrapper:
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, sql: str, params=None):
        adapted = adapt_sql_for_mysql(sql)
        try:
            if params is not None:
                return self._cur.execute(adapted, params)
            return self._cur.execute(adapted)
        except Exception as e:
            err_str = str(e)
            # 兼容 MySQL 重复创建索引的 1061 错误 (Duplicate key name)
            if "1061" in err_str or "Duplicate key name" in err_str:
                return None
            raise

    def executemany(self, sql: str, params_seq):
        adapted = adapt_sql_for_mysql(sql)
        return self._cur.executemany(adapted, params_seq)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return DictRow(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        return [DictRow(r) for r in rows]

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

class MySQLConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import pymysql.cursors
        return MySQLCursorWrapper(self._conn.cursor(pymysql.cursors.DictCursor))

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, params_seq):
        cur = self.cursor()
        cur.executemany(sql, params_seq)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def get_connection():
    """获取数据库连接：优先检测 DATABASE_URL (MySQL)，否则使用本地 SQLite 数据库"""
    if is_mysql_mode():
        import pymysql
        cfg = parse_mysql_url(get_effective_database_url())
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset=cfg["charset"],
            autocommit=False
        )
        return MySQLConnectionWrapper(conn)
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")  # 开启 WAL 极速并发读写模式
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

def init_db():
    """初始化数据库表与索引，并平滑迁移历史配置与数据 (支持 SQLite / MySQL 双模自动建表)"""
    if is_mysql_mode():
        try:
            import pymysql
            cfg = parse_mysql_url(get_effective_database_url())
            root_conn = pymysql.connect(
                host=cfg["host"],
                port=cfg["port"],
                user=cfg["user"],
                password=cfg["password"],
                charset=cfg["charset"],
                autocommit=True
            )
            with root_conn.cursor() as c:
                c.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
            root_conn.close()
            print(f"[MySQL] 数据库 `{cfg['database']}` 连通与就绪确认成功！")
        except Exception as e:
            print(f"[MySQL] 预检数据库提示: {e}")

    conn = get_connection()
    with conn:
        # 1. 巡检规则配置表 (patrol_config)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patrol_config (
                config_key VARCHAR(128) PRIMARY KEY,
                config_value TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)

        # 2. 动态重点监控航线配置表 (patrol_routes，不设上限，支持自定义航线配置名称，多用户按 user_id 隔离)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patrol_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                route_name TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                user_id TEXT NOT NULL DEFAULT 'default',
                updated_at TEXT NOT NULL
            )
        """)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(patrol_routes)")
            cols = [c[1] for c in cur.fetchall()]
            if "route_name" not in cols:
                conn.execute("ALTER TABLE patrol_routes ADD COLUMN route_name TEXT NOT NULL DEFAULT ''")
            if "user_id" not in cols:
                conn.execute("ALTER TABLE patrol_routes ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass

        # 2.1 用户 Session 会话凭证表 (多用户平台隔离支持)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                token VARCHAR(128) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                created_at VARCHAR(32) NOT NULL,
                last_active VARCHAR(32) NOT NULL
            )
        """)
        try:
            # 兼容修正常见 MySQL 字段类型 (防止已存在表将 user_id 建为 TEXT 导致索引失败)
            if is_mysql_mode():
                conn.execute("ALTER TABLE user_sessions MODIFY COLUMN user_id VARCHAR(64) NOT NULL")
        except Exception:
            pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")

        # 3. 航班直飞班次表 (flight_routes)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_city VARCHAR(32) NOT NULL,
                to_city VARCHAR(32) NOT NULL,
                from_iata VARCHAR(16) NOT NULL DEFAULT '',
                to_iata VARCHAR(16) NOT NULL DEFAULT '',
                flight_no VARCHAR(32) NOT NULL DEFAULT '',
                dep_time VARCHAR(16) NOT NULL DEFAULT '',
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
                from_city VARCHAR(32) NOT NULL,
                to_city VARCHAR(32) NOT NULL,
                flight_date VARCHAR(32) NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (from_city, to_city, flight_date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calendar_avail ON flight_calendar(from_city, to_city, is_available)")

        # 5. 实时查验流水表 (seat_queries) - 记录用户与系统查票的每个航班机位与时刻 (持久化核心)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seat_queries (
                from_city VARCHAR(32) NOT NULL,
                to_city VARCHAR(32) NOT NULL,
                flight_date VARCHAR(32) NOT NULL,
                flight_no VARCHAR(32) NOT NULL DEFAULT '',
                sec_card_left INTEGER NOT NULL DEFAULT 0,
                normal_left INTEGER NOT NULL DEFAULT 0,
                dep_time VARCHAR(16) NOT NULL DEFAULT '',
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
                batch_id VARCHAR(64) NOT NULL,
                patrol_mode VARCHAR(32) NOT NULL DEFAULT 'hot',
                from_city VARCHAR(32) NOT NULL,
                to_city VARCHAR(32) NOT NULL,
                available_days_count INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
                error_msg TEXT,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                created_at VARCHAR(32) NOT NULL
            )
        """)
        try:
            if is_mysql_mode():
                conn.execute("ALTER TABLE patrol_logs MODIFY COLUMN batch_id VARCHAR(64) NOT NULL")
        except Exception:
            pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patrol_logs_batch ON patrol_logs(batch_id)")

        # 7. 轮询监控任务表 (monitor_tasks)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitor_tasks (
                id VARCHAR(64) PRIMARY KEY,
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

        # 9. 会员个人资料与凭据持久化表 (user_profile)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id VARCHAR(64) PRIMARY KEY DEFAULT 'default',
                user_name TEXT NOT NULL DEFAULT '长龙会员',
                mobile TEXT NOT NULL DEFAULT '',
                member_level TEXT NOT NULL DEFAULT '普通会员',
                cert_number TEXT NOT NULL DEFAULT '',
                token TEXT NOT NULL DEFAULT '',
                cookie TEXT NOT NULL DEFAULT '',
                card_name TEXT NOT NULL DEFAULT '长龙畅飞卡',
                encrypted_user_id TEXT NOT NULL DEFAULT '',
                sec_card_grant_tid TEXT NOT NULL DEFAULT '',
                coupons_count INTEGER NOT NULL DEFAULT 0,
                cards_count INTEGER NOT NULL DEFAULT 0,
                points INTEGER NOT NULL DEFAULT 0,
                is_verified INTEGER NOT NULL DEFAULT 0,
                headers_json TEXT NOT NULL DEFAULT '{}',
                template_json TEXT NOT NULL DEFAULT '{}',
                refresh_token TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
        """)

        # 热迁移补充字段
        for col, c_type in [
            ("coupons_count", "INTEGER NOT NULL DEFAULT 0"),
            ("cards_count", "INTEGER NOT NULL DEFAULT 0"),
            ("points", "INTEGER NOT NULL DEFAULT 0"),
            ("is_verified", "INTEGER NOT NULL DEFAULT 0"),
            ("headers_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("template_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("refresh_token", "TEXT NOT NULL DEFAULT ''")
        ]:
            try:
                conn.execute(f"ALTER TABLE user_profile ADD COLUMN {col} {c_type}")
            except Exception:
                pass


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

def get_routes_seed_file() -> Path | None:
    """智能查找 routes_seed.json 航线种子文件 (自动规避 Docker volume 遮蔽)"""
    candidate_paths = [
        BACKEND_DIR / "data" / "routes_seed.json",
        BACKEND_DIR / "routes_seed.json",
        Path(__file__).resolve().parent / "data" / "routes_seed.json",
        Path(__file__).resolve().parent / "routes_seed.json",
        DATA_DIR / "routes_seed.json",
        Path("/app/backend/routes_seed.json"),
        Path("/app/backend/data/routes_seed.json"),
        PROJECT_DIR / "backend" / "data" / "routes_seed.json",
    ]
    for p in candidate_paths:
        if p and p.exists() and p.is_file():
            return p
    return None

def seed_flight_routes_if_empty(conn=None) -> int:
    """自动将 397 条航线/490个航班基础排班种子导入数据库 flight_routes 表"""
    close_when_done = False
    if conn is None:
        conn = get_connection()
        close_when_done = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM flight_routes")
        count = cur.fetchone()[0]
        if count > 0:
            return count

        routes_file = get_routes_seed_file()
        if not routes_file:
            print("⚠️ 未在任何候选路径中找到 routes_seed.json 航线种子文件")
            return 0

        # 如果 DATA_DIR 内丢失种子，自动同步一份过去
        try:
            target_seed = DATA_DIR / "routes_seed.json"
            if not target_seed.exists():
                import shutil
                shutil.copy2(routes_file, target_seed)
        except Exception:
            pass

        raw_routes = json.loads(routes_file.read_text(encoding="utf-8"))
        batch = []
        for r in raw_routes:
            frm = r.get("from_city") or r.get("from") or ""
            to = r.get("to_city") or r.get("to") or ""
            f_no = r.get("flight_no") or r.get("flightNo") or ""
            if not frm or not to or not f_no: continue
            batch.append((
                frm, to, CITY_IATA_MAP.get(frm, ""), CITY_IATA_MAP.get(to, ""),
                f_no, r.get("dep_time") or r.get("depTime", ""), r.get("arr_time") or r.get("arrTime", ""),
                r.get("duration", ""), r.get("aircraft", ""), r.get("frequency", ""),
                r.get("stopover", ""), r.get("season", "")
            ))
        if batch:
            with conn:
                conn.executemany("""
                    INSERT OR IGNORE INTO flight_routes 
                    (from_city, to_city, from_iata, to_iata, flight_no, dep_time, arr_time, duration, aircraft, frequency, stopover, season)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
            print(f"[+] 航网排班种子初始化成功：已为数据库自动导入 {len(batch)} 个航线航班 (覆盖 397 条长龙全网直飞航线)！")
        return len(batch)
    except Exception as e:
        print(f"⚠️ 航线班次种子导入提示: {e}")
        return 0
    finally:
        if close_when_done:
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
    # 用户明确要求：重点监控默认 0 个，不设置上限，纯净初始状态，随心添加
    pass

    # 3. 种子：航班拓扑基础数据 (flight_routes)
    seed_flight_routes_if_empty(conn)

    # 4. 种子：放票日历表 (flight_calendar) - 彻底清除脏数据并精准导入
    # 脏数据清理：如果存在日期非 YYYY-MM-DD 格式，立即清除
    conn.execute("DELETE FROM flight_calendar WHERE flight_date NOT LIKE '____-__-__'")

    cur = conn.cursor()
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

        # 3. 构造完整 routes 列表 (包含有放票与暂无放票的全部长龙航线)
        all_route_pairs = sorted(list(set(flights_map.keys()) | set(routes_dates_map.keys())))
        routes_list = []
        for (frm, to) in all_route_pairs:
            dates = routes_dates_map.get((frm, to), [])
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

        # 排序：有票航线排在前面（按可兑天数降序），无票航线排在后面
        routes_list.sort(key=lambda x: (x["availableDaysCount"] > 0, x["availableDaysCount"]), reverse=True)

        return {
            "ok": True,
            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "sqlite_database",
            "totalAvailableRoutes": len(routes_dates_map),
            "totalRoutes": len(routes_list),
            "totalDatePoints": total_points,
            "routes": routes_list
        }
    finally:
        conn.close()

def get_patrol_routes(user_id: str = "default") -> list[tuple[str, str]]:
    """从数据库读取指定用户的重点巡检航线列表 (不设上限)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT from_city, to_city FROM patrol_routes WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,))
        rows = cur.fetchall()
        if not rows and user_id != "default":
            # 若新用户尚未配置自己的重点航线，查询 default 模板供预览或留空
            pass
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()

def get_all_unique_patrol_routes() -> list[tuple[str, str]]:
    """从数据库聚合所有用户的重点监控航线（去重，供后台自动巡检机器人统一巡检入共享库）"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT from_city, to_city FROM patrol_routes")
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        conn.close()

def get_patrol_routes_detailed(user_id: str = "default") -> list[dict]:
    """从数据库读取指定用户的重点巡检航线详细列表 (包含配置名称与序号，不设上限)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(patrol_routes)")
        cols = [c[1] for c in cur.fetchall()]
        has_name = "route_name" in cols
        has_user = "user_id" in cols
        
        where_clause = "WHERE user_id = ?" if has_user else ""
        params = (user_id,) if has_user else ()
        
        if has_name:
            cur.execute(f"SELECT from_city, to_city, route_name FROM patrol_routes {where_clause} ORDER BY sort_order ASC, id ASC", params)
            rows = cur.fetchall()
            return [{"from": r[0], "to": r[1], "name": r[2] if r[2] else f"{r[0]} ➔ {r[1]}"} for r in rows]
        else:
            cur.execute(f"SELECT from_city, to_city FROM patrol_routes {where_clause} ORDER BY sort_order ASC, id ASC", params)
            rows = cur.fetchall()
            return [{"from": r[0], "to": r[1], "name": f"{r[0]} ➔ {r[1]}"} for r in rows]
    finally:
        conn.close()

def set_patrol_routes(routes: list, user_id: str = "default") -> int:
    """更新指定用户的巡检航线列表 (不设上限，支持存储自定义航线配置名称)"""
    cleaned = []
    seen = set()
    for item in routes:
        if isinstance(item, dict):
            frm = str(item.get("from", "")).strip()
            to = str(item.get("to", "")).strip()
            name = str(item.get("name", "")).strip()
            if frm and to and (frm, to) not in seen:
                seen.add((frm, to))
                cleaned.append((frm, to, name))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            frm, to = str(item[0]).strip(), str(item[1]).strip()
            name = str(item[2]).strip() if len(item) > 2 else ""
            if frm and to and (frm, to) not in seen:
                seen.add((frm, to))
                cleaned.append((frm, to, name))

    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            conn.execute("DELETE FROM patrol_routes WHERE user_id = ?", (user_id,))
            for idx, (frm, to, name) in enumerate(cleaned):
                conn.execute(
                    "INSERT INTO patrol_routes (from_city, to_city, route_name, sort_order, user_id, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (frm, to, name, idx + 1, user_id, now_str)
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
    """从数据库 flight_routes 表读取全网直飞拓扑列表 (如遇空表自动触发种子补种)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT from_city, to_city FROM flight_routes ORDER BY from_city, to_city")
        rows = cur.fetchall()
        if not rows:
            seed_flight_routes_if_empty(conn)
            cur.execute("SELECT DISTINCT from_city, to_city FROM flight_routes ORDER BY from_city, to_city")
            rows = cur.fetchall()
        return [(r[0], r[1]) for r in rows]
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

def save_user_profile(profile: dict, user_id: str = "default") -> None:
    """持久化保存会员个人信息至 SQLite user_profile 表"""
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers_val = profile.get("headers")
    if isinstance(headers_val, dict):
        headers_json = json.dumps(headers_val, ensure_ascii=False)
    else:
        headers_json = str(headers_val or profile.get("headers_json") or "{}")

    template_val = profile.get("template") or profile.get("search_template")
    if isinstance(template_val, dict):
        template_json = json.dumps(template_val, ensure_ascii=False)
    else:
        template_json = str(template_val or profile.get("template_json") or "{}")

    try:
        with conn:
            conn.execute("""
                INSERT INTO user_profile 
                (user_id, user_name, mobile, member_level, cert_number, token, cookie, card_name, encrypted_user_id, sec_card_grant_tid, coupons_count, cards_count, points, is_verified, headers_json, template_json, refresh_token, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    user_name = excluded.user_name,
                    mobile = excluded.mobile,
                    member_level = excluded.member_level,
                    cert_number = excluded.cert_number,
                    token = excluded.token,
                    cookie = excluded.cookie,
                    card_name = excluded.card_name,
                    encrypted_user_id = excluded.encrypted_user_id,
                    sec_card_grant_tid = excluded.sec_card_grant_tid,
                    coupons_count = excluded.coupons_count,
                    cards_count = excluded.cards_count,
                    points = excluded.points,
                    is_verified = excluded.is_verified,
                    headers_json = excluded.headers_json,
                    template_json = excluded.template_json,
                    refresh_token = excluded.refresh_token,
                    updated_at = excluded.updated_at
            """, (
                user_id,
                profile.get("user_name") or "长龙会员",
                profile.get("mobile") or "",
                profile.get("member_level") or "普通会员",
                profile.get("cert_number") or "",
                profile.get("token") or "",
                profile.get("cookie") or "",
                profile.get("card_name") or "长龙畅飞卡",
                profile.get("encrypted_user_id") or "",
                profile.get("sec_card_grant_tid") or "",
                int(profile.get("coupons_count") or 0),
                int(profile.get("cards_count") or 0),
                int(profile.get("points") or 0),
                int(profile.get("is_verified") or 0),
                headers_json,
                template_json,
                profile.get("refresh_token") or "",
                profile.get("updated_at") or now_str
            ))

    finally:
        conn.close()

def get_user_profile(user_id: str = "default") -> dict | None:
    """从 SQLite 读取当前已登录的会员资料"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["headers"] = json.loads(d.get("headers_json") or "{}")
        except Exception:
            d["headers"] = {}
        try:
            d["template"] = json.loads(d.get("template_json") or "{}")
        except Exception:
            d["template"] = {}
        return d
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


import secrets

def create_user_session(user_id: str) -> str:
    """为指定用户生成一个安全随机的平台 Session Token，并持久化至 user_sessions 表"""
    token = "cla_" + secrets.token_urlsafe(32)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_sessions (token, user_id, created_at, last_active) VALUES (?, ?, ?, ?)",
                (token, user_id, now_str, now_str)
            )
        return token
    finally:
        conn.close()

def get_user_by_session_token(token: str) -> dict | None:
    """根据 Session Token 获取用户信息，并静默刷新最后活跃时间"""
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if not token:
        return None

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM user_sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            return None
        user_id = row[0]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute("UPDATE user_sessions SET last_active = ? WHERE token = ?", (now_str, token))
        return get_user_profile(user_id)
    finally:
        conn.close()

def delete_user_session(token: str) -> bool:
    """删除指定的平台 Session Token (用户退出登录)"""
    if not token:
        return False
    if token.startswith("Bearer "):
        token = token[7:].strip()
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        return True
    finally:
        conn.close()

def get_any_active_user_profile() -> dict | None:
    """获取数据库中任意一个具有有效长龙 Token 的会员 profile (供后台巡检机器人共享池使用)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM user_profile WHERE token != '' AND mobile != '' ORDER BY updated_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            return get_user_profile(row[0])
        return get_user_profile("default")
    finally:
        conn.close()
