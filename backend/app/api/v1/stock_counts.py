"""再导出 controllers.stock_counts。"""

from backend.app.controllers.stock_counts import *  # 兼容壳：再导出盘点控制器全部公开符号
from backend.app.controllers.stock_counts import router  # 兼容壳：再导出盘点路由对象
