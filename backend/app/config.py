import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

LLM_API_URL = os.environ.get("LLM_API_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL")

# util(利用率) 三口径公式里的分母系数：quota(单产品配额) x PPT_QUOTA_MULTIPLIER = 20
# 六周累计版反推确认：PPT配额10 + 推文配额10 = 20
QUOTA_PRODUCT_COUNT = 2

DEFAULT_PPT_COST_EDGES = [10, 20, 30, 50, 80, 120, 200]
DEFAULT_ART_COST_EDGES = [3, 6, 10, 15, 25, 50]

STRENGTH_LIGHT_MAX = 2
STRENGTH_MEDIUM_MAX = 9

# ———————— 神笔小罗 Insight(PRD v1.1) ————————
# 本地库换成新文件，避免和旧周报累计看板的 app.db 表结构冲突(旧库保留不动)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'insight.db'}")

# local = 本地三份上传文件 + mock 补齐；vendor = 商汤接口(尚未接入，见 vendor/vendor_adapter.py)
DATA_SOURCE = os.environ.get("DATA_SOURCE", "local")
# 为 0 时关闭 mock：缺失字段一律为空/待接入，只展示真实数据
MOCK_FILL = os.environ.get("MOCK_FILL", "1") != "0"

PLATFORM_LAUNCH_DATE = "2026-07-01"          # 累计口径/本年累计花费起点(三·5、1.3)
BUDGET_PER_MONTH = {"PLUS": 600, "SUPER": 1200}
WARN_IMPORT_RATE = 40.0   # 导入率 < 40% 预警
WARN_ACTIVE_RATE = 40.0   # 活跃率 < 40% 预警
WARN_SILENT_RATE = 30.0   # 沉默率 > 30% 预警
SILENT_DAYS = 60            # 沉默：截至统计截止日连续 60 天无使用(PRD 最新版)
SILENT_MIN_OPEN_DAYS = 60   # 开通满 60 天才判定沉默
DORMANT_DAYS = 30           # 休眠：按自然月即超过 30 天没有使用、不满 60 天(说明用，休眠=未使用且非沉默)
POSTER_LIVE = os.environ.get("POSTER_LIVE", "0") == "1"  # 海报上线前不显示海报数据
METRIC_VERSION = "prd-v1.1"

# PRD 2.2 风险预警「功能使用规模或使用深度偏低」——PRD 未给阈值，按暂定预警线处理，可调：
WARN_DEPTH_RATIO = 0.5   # 单活跃账号功能使用次数 < 整体水平的 50% 视为使用深度偏低
WARN_SCALE_RATIO = 0.5   # 有效功能操作总次数 < 各分组均值的 50% 视为使用规模偏低

# ———————— 乙方(商汤)接口，DATA_SOURCE=vendor 时使用，见 docs/vendor-api-spec.md ————————
VENDOR_API_BASE_URL = os.environ.get("VENDOR_API_BASE_URL", "")
VENDOR_API_TOKEN = os.environ.get("VENDOR_API_TOKEN", "")          # 服务间鉴权 [TBD]，有值时以 Bearer 发送
VENDOR_TIMEOUT = float(os.environ.get("VENDOR_TIMEOUT", "30"))
VENDOR_PAGE_SIZE = int(os.environ.get("VENDOR_PAGE_SIZE", "5000"))
VENDOR_CACHE_TTL = float(os.environ.get("VENDOR_CACHE_TTL", "300"))  # 秒；Dataset 缓存时长
# 乙方 costDaily 分币种返回 amountCny / amountUsd，不换算；人民币总额 = ΣCNY + ΣUSD × 汇率(调用方自定)。
# 7.20 仅为占位值(与乙方文档示例一致)，上线前请按财务口径在 env 里改成实际汇率。
USD_CNY_RATE = float(os.environ.get("USD_CNY_RATE", "7.20"))
if USD_CNY_RATE <= 0:
    raise RuntimeError(f"USD_CNY_RATE 必须大于 0，当前为 {USD_CNY_RATE}")
# 统一门户接口(daList/accountList/accountTypeHistory/quotaConfig/userRoleInfo)的路径前缀 [TBD]：以门户接口文档为准
VENDOR_PORTAL_API_PREFIX = os.environ.get("VENDOR_PORTAL_API_PREFIX", "/api/shenbiDashboardApi")
# 文档 §4.1 备注：identity=other 的归属 [TBD]。employee=按员工，customer=按客户，test=按测试账号剔除
VENDOR_OTHER_IDENTITY = os.environ.get("VENDOR_OTHER_IDENTITY", "employee")
