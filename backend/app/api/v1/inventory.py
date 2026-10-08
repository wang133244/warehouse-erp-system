"""再导出 controllers.inventory。"""

from backend.app.controllers.inventory import *  # 兼容壳：再导出库存查询控制器全部公开符号
from backend.app.controllers.inventory import router  # 兼容壳：再导出库存查询路由对象
