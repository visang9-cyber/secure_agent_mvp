import calendar
import random
from datetime import date

from app.agents.base_agent import BaseAgent
from app.core.config import settings

# Seoul seasonal mock data
_MONTHLY = {
    1:  {"min": -6, "max":  2, "conds": ["snow","cloudy","clear"],                    "w": [2,3,5]},
    2:  {"min": -4, "max":  5, "conds": ["snow","cloudy","clear"],                    "w": [1,3,6]},
    3:  {"min":  3, "max": 12, "conds": ["rain","cloudy","partly_cloudy","clear"],    "w": [2,2,3,3]},
    4:  {"min":  9, "max": 19, "conds": ["rain","cloudy","partly_cloudy","clear"],    "w": [1,2,3,4]},
    5:  {"min": 14, "max": 24, "conds": ["rain","cloudy","partly_cloudy","clear"],    "w": [2,2,3,3]},
    6:  {"min": 18, "max": 28, "conds": ["heavy_rain","rain","cloudy","partly_cloudy"],"w":[2,3,3,2]},
    7:  {"min": 22, "max": 30, "conds": ["heavy_rain","rain","cloudy","clear"],       "w": [3,4,2,1]},
    8:  {"min": 22, "max": 31, "conds": ["heavy_rain","rain","cloudy","clear"],       "w": [3,3,2,2]},
    9:  {"min": 16, "max": 26, "conds": ["rain","partly_cloudy","clear"],             "w": [1,3,6]},
    10: {"min":  9, "max": 20, "conds": ["cloudy","partly_cloudy","clear"],           "w": [1,2,7]},
    11: {"min":  2, "max": 12, "conds": ["cloudy","partly_cloudy","clear"],           "w": [2,3,5]},
    12: {"min": -4, "max":  4, "conds": ["snow","cloudy","clear"],                    "w": [2,3,5]},
}

_ICONS = {
    "clear":        "☀️",
    "partly_cloudy":"⛅",
    "cloudy":       "☁️",
    "rain":         "🌧️",
    "heavy_rain":   "⛈️",
    "snow":         "❄️",
}


class WeatherAgent(BaseAgent):
    def __init__(self):
        super().__init__("WeatherAgent")

    async def run(self, **kwargs) -> dict:
        year: int = kwargs.get("year", date.today().year)
        month: int = kwargs.get("month", date.today().month)
        location: str = kwargs.get("location", "서울")

        if settings.weather_api_key:
            data = await self._fetch_real(year, month, location)
        else:
            data = self._mock(year, month, location)

        return {"type": "weather_calendar", "data": data}

    def _mock(self, year: int, month: int, location: str) -> dict:
        info = _MONTHLY[month]
        days_in_month = calendar.monthrange(year, month)[1]
        rng = random.Random(year * 100 + month)

        days = []
        for day in range(1, days_in_month + 1):
            cond = rng.choices(info["conds"], weights=info["w"])[0]
            temp_var = rng.randint(-2, 2)
            days.append({
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "condition": cond,
                "icon": _ICONS[cond],
                "min_temp": info["min"] + temp_var,
                "max_temp": info["max"] + temp_var,
            })

        return {"year": year, "month": month, "location": location, "days": days}

    async def _fetch_real(self, year: int, month: int, location: str) -> dict:
        # Real OpenWeatherMap integration placeholder
        # Falls back to mock (14일 이후는 climatological)
        return self._mock(year, month, location)
