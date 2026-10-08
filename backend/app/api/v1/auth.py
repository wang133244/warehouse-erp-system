"""再导出 controllers.auth，无业务逻辑。"""

from backend.app.controllers.auth import *  # 兼容壳：再导出认证控制器全部公开符号
from backend.app.controllers.auth import router  # 兼容壳：再导出认证路由对象
