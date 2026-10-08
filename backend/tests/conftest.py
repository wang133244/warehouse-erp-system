"""pytest 夹具：测试关闭写文件日志等。"""

import os  # import os

os.environ.setdefault("LOG_TO_FILE", "false")  # os.environ.setdefault('L

import pytest  # import pytest

from backend.app.core.cache import reset_cache  # from backend.app.core.ca


@pytest.fixture(autouse=True)  # @pytest.fixture(autouse=
def _reset_process_cache() -> None:  # def _reset_process_cache
    reset_cache()  # reset_cache()
    yield  # yield
    reset_cache()  # reset_cache()
