"""再导出 controllers.approvals。"""

from backend.app.controllers.approvals import *  # 兼容壳：再导出审批控制器全部公开符号
from backend.app.controllers.approvals import router  # 兼容壳：再导出审批路由对象
