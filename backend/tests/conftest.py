import os
import tempfile

# 必须在导入 app 之前设置：测试用独立临时库，不碰 data/insight.db
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
