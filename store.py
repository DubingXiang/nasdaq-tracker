"""
存储模块 — SQLite / PostgreSQL 自适应
"""
import sqlite3
from datetime import datetime, timedelta
from config import DB_CONFIG, IS_POSTGRES


def _get_conn():
    if IS_POSTGRES:
        import psycopg2
        return psycopg2.connect(DB_CONFIG)
    conn = sqlite3.connect(DB_CONFIG, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _adapt(sql):
    """PostgreSQL 用 %s，SQLite 用 ?"""
    return sql if IS_POSTGRES else sql.replace("%s", "?")


def _as_dicts(cur):
    """统一返回字典列表"""
    if IS_POSTGRES:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    return [dict(r) for r in cur.fetchall()]


def _as_dict(cur):
    """返回单条字典"""
    rows = _as_dicts(cur)
    return rows[0] if rows else None


def init_db():
    """建表"""
    pk = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS indicators (
                id {pk},
                date TEXT UNIQUE,
                price REAL, pe REAL, cape REAL,
                drawdown REAL, treasury REAL, vxn REAL,
                score REAL, signal TEXT, details TEXT
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS signals (
                id {pk},
                date TEXT, score REAL,
                signal TEXT, reason TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_indicators(data, valuation):
    """保存当日指标和评分"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if IS_POSTGRES:
            cur.execute(_adapt("""
                INSERT INTO indicators (date,price,pe,cape,drawdown,treasury,vxn,score,signal,details)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (date) DO UPDATE SET
                    price=EXCLUDED.price, pe=EXCLUDED.pe, cape=EXCLUDED.cape,
                    drawdown=EXCLUDED.drawdown, treasury=EXCLUDED.treasury, vxn=EXCLUDED.vxn,
                    score=EXCLUDED.score, signal=EXCLUDED.signal, details=EXCLUDED.details
            """), (
                today, data.get("price"), data.get("pe"), data.get("cape"),
                data.get("drawdown"), data.get("treasury"), data.get("vxn"),
                valuation.get("score"), valuation.get("signal"),
                str(valuation.get("scores", {})),
            ))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO indicators
                    (date,price,pe,cape,drawdown,treasury,vxn,score,signal,details)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                today, data.get("price"), data.get("pe"), data.get("cape"),
                data.get("drawdown"), data.get("treasury"), data.get("vxn"),
                valuation.get("score"), valuation.get("signal"),
                str(valuation.get("scores", {})),
            ))

        if valuation.get("score") is not None:
            cur.execute(_adapt("""
                INSERT INTO signals (date, score, signal, reason) VALUES (%s,%s,%s,%s)
            """), (
                today, valuation["score"], valuation["signal"],
                f"PE={data.get('pe')}, CAPE={data.get('cape')}, DD={data.get('drawdown')}%",
            ))
        conn.commit()
    finally:
        conn.close()


def get_latest():
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM indicators ORDER BY date DESC LIMIT 1")
        return _as_dict(cur)
    finally:
        conn.close()


def get_history(days=30):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute(_adapt("SELECT * FROM indicators WHERE date >= %s ORDER BY date ASC"), (since,))
        return _as_dicts(cur)
    finally:
        conn.close()


def get_signals(limit=20):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt("SELECT * FROM signals ORDER BY date DESC LIMIT %s"), (limit,))
        return _as_dicts(cur)
    finally:
        conn.close()


def get_record_count():
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM indicators")
        return cur.fetchone()[0]
    finally:
        conn.close()
