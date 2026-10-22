#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 畅飞卡 398 航线受控双并发全网大盘扫描器
======================================================
模式：受控双并发 (2个工作线程交替错峰，发包频率严格限制为约 1 次/秒)
目标：一次性拉取全国全部 398 条直飞拓扑未来 45 天官方兑换日历
成果：输出至 backend/data/full_network_calendar.json，带断点续存与容灾
"""
from __future__ import annotations
import json, os, queue, random, sys, threading, time
from datetime import datetime
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

OUT_FILE = DATA_DIR / "full_network_calendar.json"
PARTIAL_FILE = DATA_DIR / "full_network_calendar_partial.json"

class RateLimiter:
    """全局速率控制器：确保两个线程发包间隔严格 ≥ min_interval 秒，并带随机微抖动"""
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
    routes_path = BACKEND_DIR / "data" / "flight-routes.json"
    if not routes_path.exists():
        routes_path = PROJECT_DIR / "backend" / "data" / "flight-routes.json"
    if not routes_path.exists():
        routes_path = PROJECT_DIR / "data" / "flight-routes.json"
    rows = json.loads(routes_path.read_text(encoding="utf-8"))
    
    unique_pairs = []
    seen = set()
    for r in rows:
        frm = r.get("from")
        to = r.get("to")
        if frm and to:
            key = (frm, to)
            if key not in seen:
                seen.add(key)
                unique_pairs.append(key)
    return unique_pairs

def main():
    print("=" * 65)
    print("✈️ 长龙航空 · 畅飞卡 398 航线受控双并发全网大盘扫描启动")
    print("=" * 65)
    
    client = SecCardClient()
    if not client.headers:
        print("❌ 未能读取有效登录凭证，请检查 backend/data/cl.saz (或 changlong.saz)")
        sys.exit(1)
        
    all_routes = load_all_routes()
    total = len(all_routes)
    print(f"📊 加载完成：待扫描直飞航线共 {total} 条")
    print(f"⚙️ 运行模式：受控双并发（2 Workers 错峰交替，速度 ~1.1秒/条）")
    print(f"⏱️ 预计总耗时：约 6.5 ~ 7.5 分钟\n")

    # 如果有中断的 partial 文件，自动断点续扫
    results = {}
    if PARTIAL_FILE.exists():
        try:
            cached = json.loads(PARTIAL_FILE.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and "calendarData" in cached:
                results = cached["calendarData"]
                print(f"🔄 检测到断点续存，已恢复已扫描的 {len(results)} 条航线！")
        except Exception: pass

    # 构建工作队列
    q = queue.Queue()
    for frm, to in all_routes:
        key = f"{frm}-{to}"
        if key not in results:
            q.put((frm, to))

    remaining = q.qsize()
    print(f"🎯 本次待扫描: {remaining} 条（已完成: {len(results)} 条）\n")

    rate_limiter = RateLimiter(min_interval=1.05)
    results_lock = threading.Lock()
    progress_counter = [len(results)]
    error_list = []
    start_time = time.time()

    def worker(worker_id: str):
        while not q.empty():
            try:
                frm, to = q.get_nowait()
            except queue.Empty:
                break

            key = f"{frm}-{to}"
            rate_limiter.wait()

            success = False
            for attempt in range(3):
                try:
                    cal = client.get_calendar(frm, to)
                    with results_lock:
                        results[key] = {
                            "from": frm,
                            "to": to,
                            "calendar": cal,
                            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        progress_counter[0] += 1
                        curr = progress_counter[0]

                        # 统计该航线有无可兑票
                        has_ticket = any(v == 1 for v in cal.values()) if cal else False
                        ticket_days = sum(1 for v in cal.values() if v == 1) if cal else 0
                        status_tag = f"✅ 有票({ticket_days}天)" if has_ticket else "⚪ 已兑完/暂无"

                        # 每完成 1 条打印紧凑进度
                        elapsed = time.time() - start_time
                        avg_speed = elapsed / max(curr - (total - remaining), 1)
                        remain_sec = int(avg_speed * (total - curr))
                        print(f"[{curr:3d}/{total}] ({curr/total*100:4.1f}%) [W{worker_id}] {frm}➔{to:4s} | {status_tag} | 预计还需 {remain_sec//60}分{remain_sec%60:02d}秒")

                        # 每 25 条落盘一次防止断电/中断丢失
                        if curr % 25 == 0 or curr == total:
                            partial_payload = {
                                "lastSaved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "completed": curr,
                                "total": total,
                                "calendarData": results
                            }
                            PARTIAL_FILE.write_text(json.dumps(partial_payload, ensure_ascii=False), encoding="utf-8")

                    success = True
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "403" in err_msg or "429" in err_msg:
                        print(f"⚠️ [W{worker_id}] 触发临时频控，强制冷却 10 秒后重试 (重试 {attempt+1}/3)...")
                        time.sleep(10)
                    else:
                        time.sleep(2)

            if not success:
                with results_lock:
                    error_list.append((frm, to))
                    print(f"❌ [W{worker_id}] 航线 {frm}➔{to} 连续3次请求失败，跳过。")
            q.task_done()

    # 启动双工作线程（A 与 B 错峰并发）
    t1 = threading.Thread(target=worker, args=("A",), daemon=True)
    t2 = threading.Thread(target=worker, args=("B",), daemon=True)

    t1.start()
    time.sleep(0.55)  # 强制错开 550ms，交替进行！
    t2.start()

    t1.join()
    t2.join()

    total_time = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"🎉 全网大盘扫描完成！总耗时: {int(total_time//60)} 分 {int(total_time%60)} 秒")
    print(f"📊 成功扫描: {len(results)} / {total} 条航线，失败: {len(error_list)} 条")

    # 统计数据
    routes_with_tickets = 0
    total_ticket_instances = 0
    route_ticket_rank = []

    # 截取未来 60 天有效放票窗口
    today = datetime.now()
    if today.year < 2026: today = datetime(2026, 10, 22)
    from datetime import timedelta
    max_date_str = (today + timedelta(days=60)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    trimmed_results = {}
    for k, v in results.items():
        cal = v.get("calendar", {})
        trimmed_cal = {d: s for d, s in cal.items() if today_str <= d <= max_date_str}
        trimmed_results[k] = {
            "from": v.get("from"),
            "to": v.get("to"),
            "calendar": trimmed_cal,
            "updatedAt": v.get("updatedAt")
        }

    for k, v in trimmed_results.items():
        cal = v.get("calendar", {})
        avail_days = [d for d, status in cal.items() if status == 1]
        if avail_days:
            routes_with_tickets += 1
            total_ticket_instances += len(avail_days)
            route_ticket_rank.append((k, len(avail_days), avail_days[:3]))

    route_ticket_rank.sort(key=lambda x: x[1], reverse=True)

    final_payload = {
        "scanTimestamp": int(time.time()),
        "scanTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "calendarWindowDays": 60,
        "calendarRange": f"{today_str} ~ {max_date_str}",
        "totalRoutes": total,
        "scannedRoutes": len(trimmed_results),
        "routesWithAvailableTickets": routes_with_tickets,
        "totalAvailableDatePoints": total_ticket_instances,
        "topRoutesWithSeats": [
            {"route": r[0], "availableDaysCount": r[1], "sampleDates": r[2]}
            for r in route_ticket_rank[:30]
        ],
        "calendarData": trimmed_results
    }

    OUT_FILE.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if PARTIAL_FILE.exists():
        PARTIAL_FILE.unlink(missing_ok=True)

    print(f"💾 数据已完整固化至: backend/data/full_network_calendar.json")
    print(f"🎫 全网余票大盘速览:")
    print(f"   • 当前有可兑票航线: {routes_with_tickets} 条 (占比 {routes_with_tickets/total*100:.1f}%)")
    print(f"   • 全网可兑换日期点位: 共 {total_ticket_instances} 个出行日！")
    print(f"   • 放票最多的 TOP 10 航线:")
    for rank, (r_name, days_cnt, samples) in enumerate(route_ticket_rank[:10], 1):
        print(f"     {rank:2d}. 【{r_name}】: 可兑 {days_cnt:2d} 天 (近期如: {', '.join(samples)})")
    print("=" * 65)

if __name__ == "__main__":
    main()
