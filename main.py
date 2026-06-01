"""
纳指估值追踪器 — 入口
用法:
  python main.py                # 启动看板 + 定时任务
  python main.py --run-now      # 立即执行一次数据拉取
  python main.py --port 8080    # 指定端口
"""
import argparse
import os
import sys


def ensure_data():
    """确保数据库有数据（首次运行时拉取）"""
    from store import get_record_count, init_db
    init_db()
    if get_record_count() == 0:
        print("[Init] 首次运行，拉取初始数据...")
        from scheduler import run_daily_task
        run_daily_task()


def main():
    parser = argparse.ArgumentParser(description="纳指估值追踪器")
    parser.add_argument("--run-now", action="store_true", help="立即执行一次数据拉取")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)), help="服务端口")
    args = parser.parse_args()

    if args.run_now:
        from store import init_db
        init_db()
        from scheduler import run_daily_task
        run_daily_task()
        print("[Done] 数据已更新")
        return

    # 启动看板 + 定时任务
    ensure_data()
    from scheduler import start_scheduler
    start_scheduler()

    from app import app
    print(f"[App] 看板已启动: http://0.0.0.0:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
