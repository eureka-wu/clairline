#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡 7x24h 自动化分级巡检与防风控机器人 (SQLite 本地数据库直通驱动)
======================================================
策略架构：
1. 🌙 夜间静默避让 (默认 00:00 ~ 07:00，读取数据库配置)：全线休眠，避开长龙易盾 WAF 夜间反爬捕获；
2. ⚡ 日间热门高频巡检 (默认每 25 分钟，单条约 4.5 秒拟人间隔)：从数据库动态读取 30 条核心航线；
3. 🎯 黄金放票节点全网普查 (早 09:00 与 晚 20:00)：受控双并发遍历全量直飞拓扑；
4. 💾 实时覆盖落库：每次巡检拉取到最新放票日历，立即实时覆写入 SQLite 数据库并记录监控流水！

CLI 参数支持：
- python backend/auto_patrol.py              # 启动 7x24h 守护进程（根据数据库规则自动分级）
- python backend/auto_patrol.py --once-hot   # 立即执行一次 Top 30 热门巡检 (测试落库)
- python backend/auto_patrol.py --once-all   # 立即执行一次全网航线全量普查
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

import db
from seccard_client import SecCardClient, CITY_IATA
# 默认 Top 30 核心热门抢兑航线 (机位流动最快，优先巡检)
DEFAULT_TOP_30_HOT_ROUTES: list[tuple[str, str]] = [
    ("杭州", "阿勒泰"), ("杭州", "喀什"), ("杭州", "克拉玛依"), ("杭州", "西双版纳"),
    ("杭州", "丽江"), ("杭州", "三亚"), ("杭州", "海口"), ("杭州", "哈尔滨"),
    ("杭州", "长春"), ("杭州", "成都"), ("杭州", "重庆"), ("杭州", "广州"),
    ("杭州", "深圳"), ("杭州", "珠海"), ("杭州", "贵阳"), ("杭州", "昆明"),
    ("杭州", "乌鲁木齐"), ("杭州", "西宁"), ("杭州", "银川"), ("杭州", "大连"),
    ("杭州", "沈阳"), ("杭州", "海拉尔"),
    ("银川", "杭州"), ("银川", "乌鲁木齐"), ("银川", "喀什"), ("银川", "三亚"), ("银川", "广州"),
    ("长春", "杭州"), ("长春", "三亚"), ("长春", "成都")
]

def load_hot_routes() -> list[tuple[str, str]]:
    """从 SQLite 数据库聚合所有用户配置的重点巡检航线 (全员去重，统一巡检并入公共库)"""
    try:
        routes = db.get_all_unique_patrol_routes()
        return routes or []
    except Exception:
        return []

class RateLimiter:
    """发包间隔控制器：确保两请求间严格遵守最小间隔并增加微抖动，模拟真人访问"""
    def __init__(self, min_interval: float = 4.2):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.last_call = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            delay = self.min_interval + random.uniform(0.1, 0.4)
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self.last_call = time.time()

def load_all_routes() -> list[tuple[str, str]]:
    """从本地 SQLite 数据库 flight_routes 表加载全国直飞航线"""
    try:
        return db.get_all_flight_routes()
    except Exception:
        return []

# 全局巡检实时状态与进度记录
PATROL_STATE = {
    "running": False,
    "mode": "idle",
    "total": 0,
    "completed": 0,
    "percent": 0,
    "success": 0,
    "failed": 0,
    "current_route": "",
    "started_at": "",
    "finished_at": "",
    "status_text": "待命状态 (无正在运行的巡检任务)"
}

def scan_routes_pool(client: SecCardClient, route_list: list[tuple[str, str]], pool_name: str, batch_id: str) -> dict:
    """受控扫描航线池，拉取放票日历并实时覆盖写入本地 SQLite 数据库"""
    total = len(route_list)
    # 动态从数据库读取巡检拟人延迟规则
    cfg = db.get_patrol_config()
    default_delay = float(cfg.get("hot_min_delay_seconds", "4.2"))
    is_hot_pool = total <= 35
    min_interval = default_delay if is_hot_pool else 1.1

    rate_limiter = RateLimiter(min_interval=min_interval) if is_hot_pool else None
    if is_hot_pool:
        print(f"  ⏱️ 节奏控制：慢速拟人巡检模式 (~{min_interval:.1f}秒/条)，安全无感，实时落库...")
    else:
        print(f"  🚀 全网普查模式：采用 4 线程受控并发池，预计 60~90 秒平滑完成全网 397 条航线普查并实时落库...")
    results = {}
    lock = threading.Lock()
    q = queue.Queue()
    for item in route_list:
        q.put(item)

    success_count = 0
    fail_count = 0

    PATROL_STATE["total"] = total
    PATROL_STATE["completed"] = 0
    PATROL_STATE["percent"] = 0
    PATROL_STATE["success"] = 0
    PATROL_STATE["failed"] = 0

    consecutive_auth_fails = 0
    abort_event = threading.Event()

    def worker():
        nonlocal success_count, fail_count, consecutive_auth_fails
        while not q.empty() and not abort_event.is_set():
            try:
                frm, to = q.get_nowait()
            except queue.Empty:
                break
            
            with lock:
                PATROL_STATE["current_route"] = [frm, to]
                mode_label = "正在慢速巡检" if is_hot_pool else "正在全网普查"
                PATROL_STATE["status_text"] = f"{mode_label}: {frm} ➔ {to} ({PATROL_STATE['completed'] + 1}/{total})"

            if rate_limiter:
                rate_limiter.wait()
            else:
                # 全量 397 条并发错峰，微延时 0.25~0.45s 既高效又稳定
                time.sleep(random.uniform(0.25, 0.45))

            t_start = time.perf_counter()
            cal_map = None
            last_err = None
            try:
                for attempt in range(2):
                    try:
                        cal_map = client.get_calendar(frm, to)
                        break
                    except Exception as e:
                        last_err = e
                        err_txt = str(e)
                        if "100001" in err_txt or "403" in err_txt or "未登录" in err_txt or "失效" in err_txt:
                            break
                        # 遭遇偶发网络超时/波动时，拟人避让 1.2 秒后自动重试一次
                        time.sleep(1.2)

                if cal_map is not None:
                    duration_ms = int((time.perf_counter() - t_start) * 1000)
                    consecutive_auth_fails = 0
                    
                    # 核心功能：数据更新实时覆盖数据库对应的数据！
                    db.save_route_calendar(frm, to, cal_map)
                    
                    # 统计有效有票出行日数量
                    avail_days = sum(1 for v in cal_map.values() if (v == 1 or v is True))
                    
                    # 巡检记录写入数据库流水表 patrol_logs
                    db.record_patrol_log(
                        batch_id=batch_id,
                        patrol_mode="hot" if is_hot_pool else "all",
                        from_city=frm,
                        to_city=to,
                        avail_count=avail_days,
                        status="SUCCESS",
                        error_msg="",
                        duration_ms=duration_ms
                    )

                    with lock:
                        key = f"{frm}-{to}"
                        results[key] = {
                            "from": frm,
                            "to": to,
                            "calendar": cal_map,
                            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        success_count += 1
                        PATROL_STATE["success"] = success_count
                        PATROL_STATE["completed"] = success_count + fail_count
                        PATROL_STATE["percent"] = round((PATROL_STATE["completed"] / total) * 100, 1) if total > 0 else 0
                        if success_count % 5 == 0 or success_count == total:
                            print(f"  ⚡ [{pool_name}] 进度: {success_count}/{total} ({PATROL_STATE['percent']}%) 已实时落库")
                else:
                    raise last_err or Exception("未知网络异常")
            except Exception as e:
                duration_ms = int((time.perf_counter() - t_start) * 1000)
                err_msg = str(e)
                db.record_patrol_log(
                    batch_id=batch_id,
                    patrol_mode="hot" if is_hot_pool else "all",
                    from_city=frm,
                    to_city=to,
                    avail_count=0,
                    status="FAILED",
                    error_msg=err_msg,
                    duration_ms=duration_ms
                )
                with lock:
                    fail_count += 1
                    PATROL_STATE["failed"] = fail_count
                    PATROL_STATE["completed"] = success_count + fail_count
                    PATROL_STATE["percent"] = round((PATROL_STATE["completed"] / total) * 100, 1) if total > 0 else 0

                # 核心安全机制：若为登录态失效 (100001)，进行自动熔断，绝不无效狂刷长龙接口！
                if "100001" in err_msg or "403" in err_msg or "未登录" in err_msg or "失效" in err_msg:
                    consecutive_auth_fails += 1
                    if consecutive_auth_fails >= 2:
                        print(f"🛑 [安全熔断] 长龙会员登录凭据已失效 (100001)，自动终止本次巡检队列，防止无效请求！")
                        PATROL_STATE["status_text"] = "已自动安全熔断：会员登录凭据已过期，请点击右上角【手机验证码登录】重新登录！"
                        abort_event.set()
                        # 清空剩余队列
                        while not q.empty():
                            try:
                                q.get_nowait()
                                q.task_done()
                            except Exception:
                                break
            finally:
                try:
                    q.task_done()
                except Exception:
                    pass

    threads = []
    # 核心热门用单线程极速温和跑 (拟人避让)；全网 397 条用 4 并发受控并发池跑 (约60~90秒)
    worker_num = 1 if is_hot_pool else 4
    for _ in range(worker_num):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    PATROL_STATE["percent"] = 100
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 【{pool_name}】巡检完成！有效拉取: {len(results)} 条，失败: {fail_count} 条，数据已实时落库")
    return results

def run_patrol_cycle(client: SecCardClient, mode: str = "hot"):
    """执行单次巡检并自动增量编译同步至数据库与前端大盘"""
    batch_id = datetime.now().strftime("B%Y%m%d%H%M%S")
    PATROL_STATE["running"] = True
    PATROL_STATE["mode"] = mode
    PATROL_STATE["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PATROL_STATE["completed"] = 0
    PATROL_STATE["total"] = len(load_hot_routes()) if mode == "hot" else len(load_all_routes())
    PATROL_STATE["percent"] = 0
    PATROL_STATE["success"] = 0
    PATROL_STATE["failed"] = 0

    # 1. 发车前健康自检：先探测一条基准航线 (杭州 ➔ 深圳) 测试登录态，如果已过期立即拦截并友好提示，不浪费时间与算力
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 执行发车前凭据健康自检...")
    try:
        client.check_and_reload()
        test_cal = client.get_calendar("杭州", "深圳")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 凭据健康自检通过，官方返回 {len(test_cal)} 天日历数据，正式启动巡检！")
    except Exception as preflight_err:
        err_msg = str(preflight_err)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 凭据自检失败: {err_msg}")
        PATROL_STATE["running"] = False
        PATROL_STATE["status_text"] = "巡检启动拦截：会员登录凭据已失效 (100001)，请点击右上角【手机验证码登录】重新登录！"
        PATROL_STATE["failed"] = 1
        raise RuntimeError("长龙会员登录凭据已失效 (100001)！请点击右上角【手机验证码登录】重新登录！")

    try:
        if mode == "hot":
            hot_routes = load_hot_routes()
            if not hot_routes:
                PATROL_STATE["running"] = False
                PATROL_STATE["status_text"] = "当前未添加任何重点监控航线，请先在设置中添加关注的航线！"
                raise RuntimeError("当前未添加任何重点监控航线，请先在右上角【航线监控】设置中添加您关注的航线！")
            new_data = scan_routes_pool(client, hot_routes, f"重点监控航线 ({len(hot_routes)}条)", batch_id)
        else:
            all_routes = load_all_routes()
            new_data = scan_routes_pool(client, all_routes, "Tier 2 全网直飞拓扑", batch_id)

        PATROL_STATE["status_text"] = f"巡检完成！成功刷新并实时覆写 {len(new_data)} 条航线至 SQLite 数据库"
        PATROL_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finally:
        PATROL_STATE["running"] = False

def run_daemon_loop(client: SecCardClient):
    """7x24h 分级守护巡检主循环 (全面遵守数据库 patrol_config 规则)"""
    print("\n" + "=" * 65)
    print("🛡️ 长龙航空 · 畅飞卡 7x24h 自动化分级巡检守护进程已启动 (SQLite 数据中枢驱动)")
    print("=" * 65)

    last_hot_time = time.time()
    last_full_dates = set()

    while True:
        try:
            # 动态实时从数据库读取规则与开关
            switches = db.get_patrol_switches()
            hot_enabled = switches.get("hot_enabled", False)
            all_enabled = switches.get("all_enabled", False)

            cfg = db.get_patrol_config()
            hot_interval = int(cfg.get("hot_interval_minutes", "25")) * 60
            night_silent = (cfg.get("night_silent_enabled", "1") == "1")
            night_start = int(cfg.get("night_start_hour", "0"))
            night_end = int(cfg.get("night_end_hour", "7"))
            full_times = db.get_full_patrol_times()

            now = datetime.now()
            hour = now.hour
            today_str = now.strftime("%Y-%m-%d")
            curr_hm = now.strftime("%H:%M")

            # 1. 判断是否处于夜间静默时段
            if night_silent and (night_start <= hour < night_end):
                print(f"[{now.strftime('%H:%M:%S')}] 🌙 当前处于夜间静默时段 ({night_start:02d}:00~{night_end:02d}:00)，休眠避让中...")
                time.sleep(300)
                continue

            # 2. 判断是否触发自定义定时全网全量普查 (至多3个时间点，仅在启用开关时按照规则执行)
            triggered_full = False
            if all_enabled:
                for t_hm in full_times:
                    slot_key = f"{today_str}-{t_hm}"
                    if curr_hm == t_hm and slot_key not in last_full_dates:
                        print(f"\n🔔 [{now.strftime('%H:%M:%S')}] 触发自定义全量普查时间点 ({t_hm})！")
                        run_patrol_cycle(client, mode="all")
                        last_full_dates.add(slot_key)
                        last_hot_time = time.time()
                        time.sleep(60)
                        triggered_full = True
                        break
            if triggered_full:
                continue

            # 3. 判断是否触发日间热门巡检 (默认每 25 分钟，仅在启用开关时按照规则执行)
            if hot_enabled and (time.time() - last_hot_time >= hot_interval):
                print(f"\n⚡ [{now.strftime('%H:%M:%S')}] 触发定时热门巡检 (周期 {hot_interval//60} 分钟)...")
                run_patrol_cycle(client, mode="hot")
                last_hot_time = time.time()

            time.sleep(30)

        except KeyboardInterrupt:
            print("\n👋 用户手动中断，巡检守护进程安全退出。")
            break
        except Exception as ex:
            print(f"⚠️ 巡检守护循环发生异常: {ex}，10秒后重试...")
            time.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="长龙航空畅飞卡自动化分级巡检脚本")
    parser.add_argument("--once-hot", action="store_true", help="立即执行单次 Top 30 核心热门巡检并退出")
    parser.add_argument("--once-all", action="store_true", help="立即执行单次全网航线全量普查并退出")
    args = parser.parse_args()

    db.init_db()
    client = SecCardClient()
    if not client.headers:
        print("=" * 65)
        print("⚠️ 未能在本地检测到有效的长龙登录凭证 (cl.saz 或 changlong.saz)")
        print("💡 请将抓包文件命名为 cl.saz，放入 backend/data/ 目录下！")
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
