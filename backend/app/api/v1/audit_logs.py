"""再导出 controllers.audit_logs。"""

from backend.app.controllers.audit_logs import *  # 兼容壳：再导出审计控制器全部公开符号
from backend.app.controllers.audit_logs import router  # 兼容壳：再导出审计路由对象
