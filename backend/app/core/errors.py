from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    """A domain error rendered by the API's stable error envelope."""

    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)