"""给服务层的短导入：from backend.app.models import Product。"""

from backend.app.db.models import *  # 再导出全部 ORM 表，缩短业务层导入路径
from backend.app.db.models import __all__  # 同步显式导出名单，避免 * 漏掉公开符号
