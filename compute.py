"""
估值计算模块 — 指标评分 + 综合信号
"""
from config import PE_MIN, PE_MAX, CAPE_MIN, CAPE_MAX, WEIGHTS


# ============== 单项评分（0-100）=============

def _score_linear(value, low, high):
    """线性映射：low→100（便宜），high→0（贵）"""
    if value is None:
        return None
    score = (high - value) / (high - low) * 100
    return max(0, min(100, score))


def score_pe(pe):
    return _score_linear(pe, PE_MIN, PE_MAX)


def score_cape(cape):
    return _score_linear(cape, CAPE_MIN, CAPE_MAX)


def score_drawdown(drawdown):
    """回撤越大越便宜：0%→50分，-30%→100分"""
    if drawdown is None:
        return None
    score = 50 + (-drawdown / 30) * 50
    return max(0, min(100, score))


def score_treasury(yield_rate):
    """利率：越低对成长股越友好"""
    if yield_rate is None:
        return None
    bands = [
        (2.5, 100), (3.0, 85), (3.5, 70),
        (4.0, 55), (4.5, 40), (5.0, 25), (5.5, 10),
    ]
    if yield_rate <= bands[0][0]:
        return bands[0][1]
    if yield_rate >= bands[-1][0]:
        return bands[-1][1]
    for i in range(len(bands) - 1):
        x0, y0 = bands[i]
        x1, y1 = bands[i + 1]
        if x0 <= yield_rate <= x1:
            ratio = (yield_rate - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return 50


def score_vxn(vxn):
    """VIX：越低越好（平静=安全）"""
    if vxn is None:
        return None
    bands = [
        (12, 100), (15, 85), (20, 70),
        (25, 55), (30, 40), (35, 25), (45, 10), (55, 0),
    ]
    if vxn <= bands[0][0]:
        return bands[0][1]
    if vxn >= bands[-1][0]:
        return bands[-1][1]
    for i in range(len(bands) - 1):
        x0, y0 = bands[i]
        x1, y1 = bands[i + 1]
        if x0 <= vxn <= x1:
            ratio = (vxn - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return 50


# ============== 指标状态 ==============

def pe_status(pe):
    if pe is None:
        return "未知", "#888"
    pct = _score_linear(pe, PE_MIN, PE_MAX)
    if pct >= 70:
        return "便宜", "#4ade80"
    if pct >= 40:
        return "适中", "#facc15"
    return "偏贵", "#f87171"


def cape_status(cape):
    if cape is None:
        return "未知", "#888"
    pct = _score_linear(cape, CAPE_MIN, CAPE_MAX)
    if pct >= 70:
        return "便宜", "#4ade80"
    if pct >= 40:
        return "适中", "#facc15"
    return "偏贵", "#f87171"


def drawdown_status(dd):
    if dd is None:
        return "未知", "#888"
    if dd > -5:
        return "高位", "#f87171"
    if dd > -10:
        return "正常回调", "#facc15"
    if dd > -20:
        return "较大回调", "#fb923c"
    return "深度回调", "#4ade80"


def treasury_status(y):
    if y is None:
        return "未知", "#888"
    if y < 3.0:
        return "宽松", "#4ade80"
    if y < 4.0:
        return "适中", "#facc15"
    if y < 5.0:
        return "偏紧", "#fb923c"
    return "紧缩", "#f87171"


def vxn_status(v):
    if v is None:
        return "未知", "#888"
    if v < 15:
        return "平静", "#4ade80"
    if v < 25:
        return "正常", "#facc15"
    if v < 35:
        return "紧张", "#fb923c"
    return "恐慌", "#f87171"


# ============== 综合评分 ==============

def compute_valuation(data):
    """
    输入 fetch_all() 的输出，返回估值评分和信号
    """
    scores = {
        "pe": score_pe(data.get("pe")),
        "cape": score_cape(data.get("cape")),
        "drawdown": score_drawdown(data.get("drawdown")),
        "treasury": score_treasury(data.get("treasury")),
        "vxn": score_vxn(data.get("vxn")),
    }

    # 加权平均（跳过 None）
    total_weight = 0
    weighted_sum = 0
    for key, sc in scores.items():
        if sc is not None:
            w = WEIGHTS.get(key, 0.1)
            weighted_sum += sc * w
            total_weight += w

    if total_weight == 0:
        return {"score": None, "signal": "数据不足", "signal_en": "no_data", "scores": scores}

    score = round(weighted_sum / total_weight, 1)

    # 信号
    if score >= 75:
        signal, signal_en = "强烈建议加仓", "strong_buy"
    elif score >= 60:
        signal, signal_en = "逢低加仓", "buy"
    elif score >= 45:
        signal, signal_en = "持有观望", "hold"
    elif score >= 30:
        signal, signal_en = "谨慎减仓", "cautious"
    else:
        signal, signal_en = "建议减仓", "sell"

    return {"score": score, "signal": signal, "signal_en": signal_en, "scores": scores}


# ============== 指标详情（用于卡片展开）=============

INDICATOR_META = {
    "pe": {
        "name": "PE-TTM",
        "full_name": "滚动市盈率（12个月）",
        "unit": "",
        "getter": lambda d: d.get("pe"),
        "formatter": lambda v: f"{v:.1f}" if v else "N/A",
        "status_fn": pe_status,
        "score_fn": score_pe,
        "description": "所有成分股的总市值 ÷ 最近12个月的总净利润。PE=25 意味着按当前盈利需25年回本。",
        "bands": [
            ("< 22", "明显便宜，历史低估区间"),
            ("22-28", "相对合理"),
            ("28-35", "偏高，科技股溢价区间"),
            ("> 35", "高估，需要高增速支撑"),
            ("> 40", "泡沫信号，历史上少见"),
        ],
    },
    "cape": {
        "name": "CAPE",
        "full_name": "席勒市盈率（Shiller PE）",
        "unit": "",
        "getter": lambda d: d.get("cape"),
        "formatter": lambda v: f"{v:.1f}" if v else "N/A",
        "status_fn": cape_status,
        "score_fn": score_cape,
        "description": "用过去10年经通胀调整后的平均盈利算PE，剔除短期周期波动。由诺奖得主席勒发明，成功预测2000年互联网泡沫。",
        "bands": [
            ("< 25", "历史低估"),
            ("25-30", "长期中枢附近"),
            ("30-40", "偏高"),
            ("40-50", "高估"),
            ("> 50", "极端泡沫（2000年互联网泡沫级别）"),
        ],
    },
    "drawdown": {
        "name": "回撤",
        "full_name": "距52周最高点回撤",
        "unit": "%",
        "getter": lambda d: d.get("drawdown"),
        "formatter": lambda v: f"{v:.1f}%" if v is not None else "N/A",
        "status_fn": drawdown_status,
        "score_fn": score_drawdown,
        "description": "当前价格比过去一年最高点跌了多少。最直观的'贵不贵'指标。",
        "bands": [
            ("> -5%", "接近历史高位，正常波动"),
            ("-5% ~ -10%", "技术性回调，常见"),
            ("-10% ~ -20%", "较大回调，可能是加仓机会"),
            ("-20% ~ -30%", "熊市区间，恐慌情绪"),
            ("< -30%", "深度熊市，历史上每次最终都涨回来"),
        ],
    },
    "treasury": {
        "name": "10Y美债",
        "full_name": "10年期美国国债收益率",
        "unit": "%",
        "getter": lambda d: d.get("treasury"),
        "formatter": lambda v: f"{v:.2f}%" if v else "N/A",
        "status_fn": treasury_status,
        "score_fn": score_treasury,
        "description": "美国政府借10年期国债付的利息，代表'无风险利率'。利率越高，未来利润折现越不值钱——对纳指成长股打击最大。PE是价格，利率是地心引力。",
        "bands": [
            ("< 3%", "宽松，成长股春风得意"),
            ("3% ~ 4%", "中性"),
            ("4% ~ 5%", "偏紧，对高估值有压制"),
            ("> 5%", "紧缩，成长股承压明显"),
        ],
    },
    "vxn": {
        "name": "VIX恐慌指数",
        "full_name": "CBOE 波动率指数（VIX）",
        "unit": "",
        "getter": lambda d: d.get("vxn"),
        "formatter": lambda v: f"{v:.1f}" if v else "N/A",
        "status_fn": vxn_status,
        "score_fn": score_vxn,
        "description": "市场对未来30天波动幅度的预期，通过期权价格算出。也叫'恐慌指数'。用 VIX 作为纳指波动率（VXN）的近似代理。",
        "bands": [
            ("< 15", "很平静——但平静太久反而要警惕"),
            ("15-25", "正常区间"),
            ("25-35", "明显紧张，市场在担心什么"),
            ("35-50", "恐慌，大家都在买保险——往往离底部不远"),
            ("> 50", "极端恐慌（2020.3疫情、2008金融危机级别）"),
        ],
    },
}


def get_indicator_details(data):
    """返回所有指标的完整详情，用于前端卡片渲染"""
    details = {}
    for key, meta in INDICATOR_META.items():
        raw = meta["getter"](data)
        sc = meta["score_fn"](raw)
        status_text, status_color = meta["status_fn"](raw)
        details[key] = {
            "name": meta["name"],
            "full_name": meta["full_name"],
            "value": raw,
            "display": meta["formatter"](raw),
            "unit": meta["unit"],
            "score": round(sc, 1) if sc is not None else None,
            "status": status_text,
            "status_color": status_color,
            "description": meta["description"],
            "bands": meta["bands"],
            "current_band": _find_current_band(raw, meta["bands"], key),
        }
    return details


def _find_current_band(value, bands, key):
    """判断当前值在哪个区间"""
    if value is None:
        return None
    if key == "drawdown":
        # drawdown 是负数
        if value > -5:
            return bands[0][0]
        if value > -10:
            return bands[1][0]
        if value > -20:
            return bands[2][0]
        if value > -30:
            return bands[3][0]
        return bands[4][0]
    # 其他指标：从小到大
    for band_label, _ in bands:
        # 提取数值边界
        nums = re.findall(r'[\d.]+', band_label)
        if not nums:
            continue
        upper = float(nums[-1])
        if value < upper:
            return band_label
    return bands[-1][0]


import re
