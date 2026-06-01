# 纳指估值追踪器

自动追踪纳斯达克100估值指标，每日计算综合评分，提供远程网页看板。

## 5大核心指标

| 指标 | 数据源 | 说明 |
|------|--------|------|
| PE-TTM | stockanalysis.com | 滚动12个月市盈率 |
| CAPE | 基于PE估算 | 席勒市盈率（PE×1.15近似） |
| 距最高点回撤 | Yahoo Finance | QQQ距52周高点跌幅 |
| 10Y美债收益率 | FRED API | 无风险利率 |
| VIX恐慌指数 | Yahoo Finance | 市场波动预期 |

## 评分逻辑

0-100分，越高越便宜：
- **75+**：强烈建议加仓
- **60-75**：逢低加仓
- **45-60**：持有观望
- **30-45**：谨慎减仓
- **<30**：建议减仓

## 本地运行

```bash
cd outputs/nasdaq-tracker

# 复制配置
cp .env.example .env
# 编辑 .env，填入 FRED_API_KEY

# 安装依赖
pip install -r requirements.txt

# 立即执行一次
python main.py --run-now

# 启动看板（浏览器打开 localhost:5000）
python main.py
```

## 部署到 Render（免费、24小时在线）

1. 推代码到 GitHub
2. 去 [render.com](https://render.com) 注册，连接 GitHub repo
3. New Web Service → 选你的 repo
4. 设置：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --threads 2 --preload`
5. Environment Variables 里添加 `FRED_API_KEY`
6. 部署完成后拿到 URL，手机电脑随时访问

### 保持服务活跃

Render 免费版15分钟无请求会休眠。用 [UptimeRobot](https://uptimerobot.com/)（免费）每14分钟 ping 一次 `/health` 端口即可保持活跃。

## 项目结构

```
nasdaq-tracker/
├── .env.example     # 配置模板
├── .env             # 实际配置（不入库）
├── requirements.txt
├── config.py        # 配置加载
├── fetcher.py       # 数据拉取
├── compute.py       # 估值计算和评分
├── store.py         # 数据库存储
├── app.py           # Flask 看板
├── scheduler.py     # 定时调度
├── main.py          # 入口
├── Procfile         # Render 部署
├── render.yaml      # Render 配置
└── templates/
    └── index.html   # 看板页面
```

## 后续可扩展

- 接入邮件/PushPlus 推送
- 接入 PostgreSQL 持久化存储
- 添加更多指标（PS、EV/EBITDA）
- 支持多指数（标普500、恒生科技）
