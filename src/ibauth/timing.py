import time
from types import TracebackType
from typing import Optional, Type


class AsyncTimer:
    def __init__(self) -> None:
        self.start: float = 0.0
        self.end: float = 0.0
        self.duration: float = 0.0

    async def __aenter__(self) -> "AsyncTimer":
        self.start = time.perf_counter()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.end = time.perf_counter()
        self.duration = self.end - self.start
