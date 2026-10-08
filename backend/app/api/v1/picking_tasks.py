"""再导出 controllers.picking_tasks。"""

from backend.app.controllers.picking_tasks import *  # 兼容壳：再导出拣货控制器全部公开符号
from backend.app.controllers.picking_tasks import router  # 兼容壳：再导出拣货路由对象
