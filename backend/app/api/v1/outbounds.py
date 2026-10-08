"""再导出 controllers.outbounds。"""

from backend.app.controllers.outbounds import *  # 兼容壳：再导出出库控制器全部公开符号
from backend.app.controllers.outbounds import router  # 兼容壳：再导出出库路由对象
