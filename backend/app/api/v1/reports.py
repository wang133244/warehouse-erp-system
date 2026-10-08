"""再导出 controllers.reports。"""

from backend.app.controllers.reports import *  # 兼容壳：再导出报表控制器全部公开符号
from backend.app.controllers.reports import router  # 兼容壳：再导出报表路由对象
