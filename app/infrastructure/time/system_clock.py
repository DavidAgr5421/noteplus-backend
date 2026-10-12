from datetime import datetime

import pytz


class SystemClock:
    """RN-10: America/Bogota."""

    def now(self) -> datetime:
        return datetime.now(tz=pytz.timezone("America/Bogota"))

    def today_in_bogota(self) -> str:
        tz = pytz.timezone("America/Bogota")
        return datetime.now(tz=tz).strftime("%Y-%m-%d")
