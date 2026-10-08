"""再导出 controllers.catalog。"""

from backend.app.controllers.catalog import *  # 兼容壳：再导出基础资料控制器全部公开符号
from backend.app.controllers.catalog import router  # 兼容壳：再导出基础资料路由对象
