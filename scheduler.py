"""
定时调度模块
"""
import time
import threading
import schedule
from config import SCHEDULER_TIME


def run_daily_task():
    """执行每日任务：拉数据 → 计算 → 存储"""
    from fetcher import fetch_all
    from compute import compute_valuation, get_indicator_details
    from store import save_indicators

    print("[Scheduler] 开始执行每日任务...")
    try:
        data = fetch_all()
        if not data.get("price"):
            print("[Scheduler] 数据拉取失败，跳过")
            return

        valuation = compute_valuation(data)
        save_indicators(data, valuation)
        print(f"[Scheduler] 完成 — 评分={valuation.get('score')}, 信号={valuation.get('signal')}")
    except Exception as e:
        print(f"[Scheduler] 任务异常: {e}")


def start_scheduler():
    """后台线程：每天定时执行任务"""
    schedule.every().day.at(SCHEDULER_TIME).do(run_daily_task)
    print(f"[Scheduler] 已启动，每天 {SCHEDULER_TIME}（北京时间）执行")

    def loop():
        while True:
            schedule.run_pending()
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
