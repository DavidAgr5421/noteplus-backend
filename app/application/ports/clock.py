from datetime import date
from typing import Protocol


class Clock(Protocol):
    def now(self) -> date: ...
    def today_in_bogota(self) -> str: ...  # YYYY-MM-DD
