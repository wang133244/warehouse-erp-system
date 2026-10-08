"""兼容旧 import；请不要在此添加新接口。"""

from backend.app.controllers.__init__ import *  # 兼容壳：再导出 controllers 包符号，本文件不含业务逻辑
from backend.app.controllers.__init__ import router  # 兼容壳：再导出 router 供旧路径挂载
