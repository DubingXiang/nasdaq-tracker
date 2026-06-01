import os
from dotenv import load_dotenv

load_dotenv()

# === API Keys ===
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# === Database ===
DATABASE_URL = os.getenv("DATABASE_URL", "")
IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    DB_CONFIG = DATABASE_URL
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")
    DB_CONFIG = DB_PATH

# === Cache ===
CACHE_TTL = int(os.getenv("CACHE_TTL", "900"))  # 15 min

# === Scheduler ===
SCHEDULER_TIME = os.getenv("SCHEDULER_TIME", "08:00")

# === Indicator historical ranges (for percentile estimation) ===
PE_MIN, PE_MAX = 18.0, 45.0
CAPE_MIN, CAPE_MAX = 20.0, 50.0

# === Scoring weights ===
WEIGHTS = {"pe": 0.30, "cape": 0.25, "drawdown": 0.15, "treasury": 0.10, "vxn": 0.20}
