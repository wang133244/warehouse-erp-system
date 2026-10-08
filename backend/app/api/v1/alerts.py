"""再导出 controllers.alerts。"""

from backend.app.controllers.alerts import *  # 兼容壳：再导出预警控制器全部公开符号
from backend.app.controllers.alerts import router  # 兼容壳：再导出预警路由对象
