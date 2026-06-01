"""
Flask 看板应用
"""
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from store import init_db, get_latest, get_history, get_signals, save_indicators
from compute import compute_valuation, get_indicator_details

app = Flask(__name__)

# 启动时初始化数据库
init_db()


@app.template_filter("cache_bust")
def cache_bust_filter(url):
    """静态资源缓存破坏"""
    return f"{url}?v={int(datetime.now().timestamp())}"


def _serialize_history(history):
    """将历史记录序列化为 JSON 可用格式"""
    result = []
    for r in history:
        result.append({
            "date": str(r.get("date", "")),
            "price": r.get("price"),
            "pe": r.get("pe"),
            "cape": r.get("cape"),
            "drawdown": r.get("drawdown"),
            "treasury": r.get("treasury"),
            "vxn": r.get("vxn"),
            "score": r.get("score"),
            "signal": r.get("signal"),
        })
    return result


# ============== 路由 ==============

@app.route("/")
def index():
    try:
        latest = get_latest()
        if latest is None:
            return render_template("index.html", no_data=True)

        # 构造 data dict 给 compute 用
        data = {
            "pe": latest.get("pe"),
            "cape": latest.get("cape"),
            "drawdown": latest.get("drawdown"),
            "treasury": latest.get("treasury"),
            "vxn": latest.get("vxn"),
        }

        valuation = compute_valuation(data)
        details = get_indicator_details(data)
        history = get_history(30)
        signals = get_signals(20)

        return render_template(
            "index.html",
            no_data=False,
            latest=latest,
            valuation=valuation,
            details=details,
            history_json=_serialize_history(history),
            signals=signals,
            updated_at=latest.get("date", datetime.now().strftime("%Y-%m-%d")),
        )
    except Exception as e:
        return render_template("index.html", no_data=True, error=str(e))


@app.route("/api/history")
def api_history():
    days = request.args.get("days", 30, type=int)
    history = get_history(days)
    return jsonify(_serialize_history(history))


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """手动触发数据刷新"""
    from fetcher import fetch_all
    try:
        data = fetch_all()
        if not data.get("price"):
            return jsonify({"error": "数据拉取失败"}), 500
        valuation = compute_valuation(data)
        save_indicators(data, valuation)
        return jsonify({"ok": True, "score": valuation.get("score"), "signal": valuation.get("signal")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})
