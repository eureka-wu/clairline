#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡 7x24h 自动化分级巡检与防风控机器人
======================================================
策略架构：
1. 🌙 夜间静默避让 (00:00 ~ 07:00)：全线休眠，避开长龙易盾 WAF 夜间反爬捕获；
2. ⚡ 日间热门高频巡检 (白天每 25 分钟)：仅巡检 Top 30 核心热门航线，耗时仅 ~30 秒，即时刷新高频机位；
3. 🎯 黄金放票节点全网普查 (早 09:00 与 晚 20:00)：受控双并发遍历 398 条全量拓扑，耗时 ~7 分钟；
4. 🔄 自动闭环：每次巡检完自动增量合并并调用 trim_calendar_60days 编译同步至前端，大盘秒级刷新！

CLI 参数支持：
- python backend/auto_patrol.py              # 启动 7x24h 守护进程（根据时间自动分级）
- python backend/auto_patrol.py --once-hot   # 立即执行一次 Top 30 热门巡检 (~30秒测试)
- python backend/auto_patrol.py --once-all   # 立即执行一次全网 398 条全量普查 (~7分钟)
"""
from __future__ import annotations
import argparse, json, queue, random, sys, threading, time
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception: pass

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

from seccard_client import SecCardClient, CITY_IATA
import trim_calendar_60days

CALENDAR_FILE = DATA_DIR / "full_network_calendar.json"
FLIGHT_ROUTES_FILE = DATA_DIR / "flight-routes.json"

HOT_ROUTES_FILE = DATA_DIR / "hot_routes.json"

# 默认 Top 30 核心热门抢兑航线 (机位流动最快，优先巡检)
DEFAULT_TOP_30_HOT_ROUTES: list[tuple[str, str]] = [
    # 杭州大本营 ➔ 疆藏避寒/滑雪/骨干航线
    ("杭州", "阿勒泰"),
    ("杭州", "喀什"),
    ("杭州", "克拉玛依"),
    ("杭州", "西双版纳"),
    ("杭州", "丽江"),
    ("杭州", "三亚"),
    ("杭州", "海口"),
    ("杭州", "哈尔滨"),
    ("杭州", "长春"),
    ("杭州", "成都"),
    ("杭州", "重庆"),
    ("杭州", "广州"),
    ("杭州", "深圳"),
    ("杭州", "珠海"),
    ("杭州", "贵阳"),
    ("杭州", "昆明"),
    ("杭州", "乌鲁木齐"),
    ("杭州", "西宁"),
    ("杭州", "银川"),
    ("杭州", "大连"),
    ("杭州", "沈阳"),
    ("杭州", "海拉尔"),

    # 银川西北大本营 ➔ 重点航线
    ("银川", "杭州"),
    ("银川", "乌鲁木齐"),
    ("银川", "喀什"),
    ("银川", "三亚"),
    ("银川", "广州"),

    # 长春东北大本营 ➔ 重点航线
    ("长春", "杭州"),
    ("长春", "三亚"),
    ("长春", "成都"),
]

def load_hot_routes() -> list[tuple[str, str]]:
    """动态从 hot_routes.json 读取前端配置的巡检航线名单 (上限30条)"""
    if HOT_ROUTES_FILE.exists():
        try:
            raw = json.loads(HOT_ROUTES_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, list) and raw:
                routes = [(str(x[0]), str(x[1])) for x in raw if len(x) >= 2][:30]
                if routes:
                    return routes
        except Exception:
            pass
    return list(DEFAULT_TOP_30_HOT_ROUTES)

class RateLimiter:
    """发包间隔控制器：确保两请求间严格遵守最小间隔并增加微抖动，模拟真人访问"""
    def __init__(self, min_interval: float = 1.05):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.last_call = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            delay = self.min_interval + random.uniform(0.05, 0.25)
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self.last_call = time.time()

def load_all_routes() -> list[tuple[str, str]]:
    """从 flight-routes.json 加载全国直飞航线"""
    if not FLIGHT_ROUTES_FILE.exists():
        return []
    try:
        rows = json.loads(FLIGHT_ROUTES_FILE.read_text(encoding="utf-8"))
        seen = set()
        routes = []
        for r in rows:
            frm, to = r.get("from"), r.get("to")
            if frm and to and (frm, to) not in seen:
                seen.add((frm, to))
                routes.append((frm, to))
        return routes
    except Exception:
        return []

def load_existing_calendar() -> dict:
    """读取现有全网日历，支持增量合并"""
    if CALENDAR_FILE.exists():
        try:
            raw = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "calendarData" in raw:
                return raw.get("calendarData", {})
        except Exception:
            pass
    return {}

def save_merged_calendar(calendar_data: dict):
    """保存并合并后的全网日历"""
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalRoutes": len(calendar_data),
        "calendarData": calendar_data
    }
    CALENDAR_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def scan_routes_pool(client: SecCardClient, route_list: list[tuple[str, str]], pool_name: str) -> dict:
    """受控双并发扫描指定的航线池并返回最新日历映射"""
    # 自适应速率：核心热门放缓至 4.2~5.2 秒/条 (拟人极低频，耗时约 2~2.5 分钟)；全量普查按 1.1 秒双并发跑
    is_hot_pool = len(route_list) <= 35
    min_interval = 4.2 if is_hot_pool else 1.1
    rate_limiter = RateLimiter(min_interval=min_interval)
    if is_hot_pool:
        print(f"  ⏱️ 节奏控制：慢速拟人巡检模式 (~4.5秒/条)，预计耗时约 2 ~ 2.5 分钟，安全无感...")
    results = {}
    lock = threading.Lock()
    q = queue.Queue()
    for item in route_list:
        q.put(item)

    success_count = 0
    fail_count = 0

    def worker():
        nonlocal success_count, fail_count
        while not q.empty():
            try:
                frm, to = q.get_nowait()
            except queue.Empty:
                break
            
            rate_limiter.wait()
            try:
                cal_map = client.get_calendar(frm, to)
                with lock:
                    key = f"{frm}-{to}"
                    results[key] = cal_map
                    success_count += 1
                    # 每 10 条或热门完成时打印进度
                    if success_count % 10 == 0 or success_count == total:
                        print(f"  ⚡ [{pool_name}] 进度: {success_count}/{total} (成功:{success_count}, 失败:{fail_count})")
            except Exception as e:
                with lock:
                    fail_count += 1
                # 静默处理单个航线异常
            finally:
                q.task_done()

    threads = []
    # 核心热门用单线程极速温和跑（避免并发特征）；全量 398 条用双并发错峰跑
    worker_num = 1 if len(route_list) <= 35 else 2
    for _ in range(worker_num):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 【{pool_name}】巡检完成！有效拉取: {len(results)} 条，失败: {fail_count} 条")
    return results

def run_patrol_cycle(client: SecCardClient, mode: str = "hot"):
    """执行单次巡检并自动增量编译同步"""
    existing_calendar = load_existing_calendar()
    
    if mode == "hot":
        hot_routes = load_hot_routes()
        new_data = scan_routes_pool(client, hot_routes, f"Tier 1 核心热门 ({len(hot_routes)}条)")
    else:
        all_routes = load_all_routes()
        new_data = scan_routes_pool(client, all_routes, "Tier 2 全网 398 直飞拓扑")

    # 增量合并
    existing_calendar.update(new_data)
    save_merged_calendar(existing_calendar)

    # 自动调用净化裁切器，同步至前端静态大盘
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 正在自动编译并同步至前端静态数据库 (trim_calendar_60days)...")
    try:
        trim_calendar_60days.main()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 前端大盘已无缝更新就绪！")
    except Exception as e:
        print(f"⚠️ 自动同步前端异常: {e}")

def run_daemon_loop(client: SecCardClient):
    """7x24h 分级守护巡检主循环"""
    print("\n" + "=" * 65)
    print("🛡️ 长龙航空 · 畅飞卡 7x24h 自动化分级巡检守护进程已启动")
    print("=" * 65)
    print("📋 巡检策略已就绪：")
    print("  • 🌙 00:00 ~ 07:00：夜间彻底静默休眠（规避风控）")
    print("  • ⚡ 白天时段 (07:00 ~ 24:00)：每 25 分钟极速巡检 Top 30 核心热门 (~30秒)")
    print("  • 🎯 早 09:00 与 晚 20:00：自动触发全网 398 航线大盘全量普查 (~7分钟)")
    print("=" * 65 + "\n")

    # 启动时先执行一次 Top 30 热门自检
    print("🚀 守护进程初始化：立即执行一次 Top 30 热门首检...")
    run_patrol_cycle(client, mode="hot")

    last_hot_time = time.time()
    last_full_dates = set()  # 记录当天已经跑过全量的日期标记 (格式: YYYY-MM-DD-09, YYYY-MM-DD-20)

    HOT_INTERVAL = 25 * 60  # 25 分钟

    while True:
        try:
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            today_str = now.strftime("%Y-%m-%d")

            # 1. 判断是否处于夜间静默时段 (00:00 ~ 07:00)
            if 0 <= hour < 7:
                print(f"[{now.strftime('%H:%M:%S')}] 🌙 当前处于夜间静默时段 (00:00~07:00)，休眠避让中 (长龙夜间不放票)...")
                time.sleep(300)  # 休眠 5 分钟
                continue

            # 2. 判断是否触发放票节点全网全量普查 (早 09:00~09:20 或 晚 20:00~20:20)
            slot_key = ""
            if hour == 9 and minute < 25:
                slot_key = f"{today_str}-09"
            elif hour == 20 and minute < 25:
                slot_key = f"{today_str}-20"

            if slot_key and slot_key not in last_full_dates:
                print(f"\n🔔 [{now.strftime('%H:%M:%S')}] 触发官方黄金放票窗口全网普查 ({slot_key})！")
                run_patrol_cycle(client, mode="all")
                last_full_dates.add(slot_key)
                last_hot_time = time.time()
                time.sleep(60)
                continue

            # 3. 判断是否触发日间热门巡检 (每 25 分钟)
            if time.time() - last_hot_time >= HOT_INTERVAL:
                print(f"\n⚡ [{now.strftime('%H:%M:%S')}] 触发定时热门巡检 (距上次 25 分钟)...")
                run_patrol_cycle(client, mode="hot")
                last_hot_time = time.time()

            # 常规轮询心跳 (每 30 秒检查一次时钟)
            time.sleep(30)

        except KeyboardInterrupt:
            print("\n👋 用户手动中断，巡检守护进程安全退出。")
            break
        except Exception as ex:
            print(f"⚠️ 巡检守护循环发生未捕获异常: {ex}，10秒后重试...")
            time.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="长龙航空畅飞卡自动化分级巡检脚本")
    parser.add_argument("--once-hot", action="store_true", help="立即执行单次 Top 30 核心热门巡检并退出")
    parser.add_argument("--once-all", action="store_true", help="立即执行单次全网 398 航线全量普查并退出")
    args = parser.parse_args()

    # 初始化长龙客户端与凭据探测
    client = SecCardClient()
    if not client.headers:
        print("=" * 65)
        print("⚠️ 未能在本地检测到有效的长龙登录凭证 (cl.saz 或 changlong.saz)")
        print("💡 请将 Fiddler 导出的抓包文件命名为 cl.saz，放入 backend/data/ 目录下！")
        print("=" * 65)
        sys.exit(1)

    if args.once_hot:
        run_patrol_cycle(client, mode="hot")
    elif args.once_all:
        run_patrol_cycle(client, mode="all")
    else:
        run_daemon_loop(client)

if __name__ == "__main__":
    main()
