"""再导出 controllers.inbounds。"""

from backend.app.controllers.inbounds import *  # 兼容壳：再导出入库控制器全部公开符号
from backend.app.controllers.inbounds import router  # 兼容壳：再导出入库路由对象
