"""再导出 controllers.followup。"""

from backend.app.controllers.followup import *  # 兼容壳：再导出后续功能控制器全部公开符号
from backend.app.controllers.followup import router  # 兼容壳：再导出名为 router 的符号以兼容旧 import
