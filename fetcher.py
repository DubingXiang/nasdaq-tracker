"""
数据拉取模块 — Yahoo Finance Chart API + FRED API
"""
import time
import re
import requests
from datetime import datetime
from config import FRED_API_KEY, CACHE_TTL

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

_cache = {}


def _cached(key, ttl=CACHE_TTL):
    def decorator(func):
        def wrapper(*args, **kwargs):
            full_key = f"{key}:{args}:{kwargs}"
            now = time.time()
            if full_key in _cache and now - _cache[full_key]["ts"] < ttl:
                return _cache[full_key]["val"]
            result = func(*args, **kwargs)
            _cache[full_key] = {"val": result, "ts": now}
            return result
        return wrapper
    return decorator


# ============== Yahoo Finance Chart API ==============

def _chart(symbol, period="1y"):
    range_map = {"5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y"}
    r = range_map.get(period, "1y")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={r}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        results = data.get("chart", {}).get("result", [])
        return results[0] if results else None
    except Exception:
        return None


# ============== 纳指数据 ==============

@_cached("nasdaq")
def fetch_nasdaq_data():
    """获取 QQQ 价格、52周高点"""
    result = {"price": None, "pe": None, "prev_close": None, "high_52w": None}

    chart = _chart("QQQ", "1y")
    if not chart:
        return result

    meta = chart.get("meta", {})
    result["price"] = meta.get("regularMarketPrice")

    # 历史数据
    closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    valid = [c for c in closes if c is not None]

    if valid:
        result["high_52w"] = max(valid)
        # 前一天收盘 = 倒数第二个有效值
        if len(valid) >= 2:
            result["prev_close"] = valid[-2]

    # PE 从网页获取
    result["pe"] = _fetch_pe()

    return result


@_cached("nasdaq_history")
def fetch_nasdaq_history(period="3mo"):
    """获取历史收盘价"""
    chart = _chart("QQQ", period)
    if not chart:
        return None
    timestamps = chart.get("timestamp", [])
    closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    result = []
    for ts, close in zip(timestamps, closes):
        if close is not None:
            result.append({
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                "close": close,
            })
    return result


# ============== PE 数据 ==============

def _fetch_pe():
    """从多个来源尝试获取纳指100 PE"""
    # 方法1: stockanalysis.com
    try:
        url = "https://stockanalysis.com/etf/qqq/financials/"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'PE\s*Ratio[^<]*<[^>]*>(\d+\.?\d*)', resp.text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 5 < val < 100:
                return val
    except Exception:
        pass

    # 方法2: wisesheets
    try:
        url = "https://wisesheets.io/qqq-pe-ratio"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'(\d+\.?\d*)\s*(?:x|times)', resp.text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 5 < val < 100:
                return val
    except Exception:
        pass

    # 方法3: 从 QQQ 的 P/E 估算 (price / EPS)
    # 2024 QQQ EPS 约 $22-25，用 $23 估算
    try:
        chart = _chart("QQQ", "5d")
        if chart:
            price = chart.get("meta", {}).get("regularMarketPrice")
            if price:
                estimated_eps = 23.5  # 2024-2025 近似
                pe = round(price / estimated_eps, 1)
                if 10 < pe < 60:
                    return pe
    except Exception:
        pass

    return None


# ============== VIX ==============

@_cached("vix")
def fetch_vix():
    """获取 VIX 指数"""
    chart = _chart("^VIX", "5d")
    if chart:
        val = chart.get("meta", {}).get("regularMarketPrice")
        if val:
            return float(val)
    return None


# ============== 美债收益率 ==============

@_cached("treasury")
def fetch_treasury_yield():
    """获取 10 年期美债收益率"""
    # FRED API
    if FRED_API_KEY:
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "DGS10",
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5,
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            for obs in data.get("observations", []):
                val = obs.get("value", ".")
                if val != ".":
                    return float(val)
        except Exception:
            pass

    # 备用：Yahoo ^TNX
    chart = _chart("^TNX", "5d")
    if chart:
        val = chart.get("meta", {}).get("regularMarketPrice")
        if val:
            return float(val)
    return None


# ============== CAPE ==============

@_cached("cape")
def fetch_cape(current_pe=None):
    """
    获取近似纳指 CAPE
    策略：纳指 CAPE 约为 PE 的 1.1-1.3 倍（基于历史比值）
    """
    if current_pe:
        return round(current_pe * 1.15, 1)

    # 如果没有 PE，尝试获取
    pe = _fetch_pe()
    if pe:
        return round(pe * 1.15, 1)

    return None


# ============== 汇总 ==============

def fetch_all():
    """拉取所有数据"""
    nasdaq = fetch_nasdaq_data()
    price = nasdaq.get("price")
    pe = nasdaq.get("pe")
    high_52w = nasdaq.get("high_52w")

    drawdown = None
    if price and high_52w and high_52w > 0:
        drawdown = round((price - high_52w) / high_52w * 100, 2)

    cape = fetch_cape(pe)
    treasury = fetch_treasury_yield()
    vix = fetch_vix()

    return {
        "price": price,
        "prev_close": nasdaq.get("prev_close"),
        "pe": pe,
        "cape": cape,
        "drawdown": drawdown,
        "treasury": treasury,
        "vxn": vix,
    }
