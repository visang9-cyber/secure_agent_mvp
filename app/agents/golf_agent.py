import random
from datetime import date, timedelta

from app.agents.base_agent import BaseAgent

_COURSES = [
    {"name": "파주 CC",       "region": "파주시",  "price": "14~18만원"},
    {"name": "베어크릭 GC",   "region": "포천시",  "price": "18~24만원"},
    {"name": "88 CC",         "region": "용인시",  "price": "20~28만원"},
    {"name": "레이크사이드 CC","region": "용인시",  "price": "22~30만원"},
    {"name": "기흥 CC",       "region": "용인시",  "price": "16~20만원"},
    {"name": "그린밸리 CC",   "region": "수원시",  "price": "12~16만원"},
    {"name": "남촌 CC",       "region": "광주시",  "price": "15~19만원"},
    {"name": "엘리시안 강촌", "region": "가평군",  "price": "20~26만원"},
    {"name": "비전힐스 CC",   "region": "이천시",  "price": "13~17만원"},
    {"name": "클럽 900",      "region": "양주시",  "price": "11~15만원"},
    {"name": "한양 CC",       "region": "양주시",  "price": "16~21만원"},
    {"name": "포천 힐스 CC",  "region": "포천시",  "price": "14~18만원"},
]

_TEE_SLOTS = [
    "06:30","07:00","07:30","08:00","08:30","09:00",
    "09:30","10:00","12:00","13:00","14:00","14:30","15:00",
]


class GolfAgent(BaseAgent):
    def __init__(self):
        super().__init__("GolfAgent")

    async def run(self, **kwargs) -> dict:
        today = date.today()
        date_from: str = kwargs.get("date_from", (today + timedelta(days=1)).isoformat())
        date_to: str   = kwargs.get("date_to",   (today + timedelta(days=7)).isoformat())
        region: str    = kwargs.get("region", "")

        start = date.fromisoformat(date_from)
        end   = date.fromisoformat(date_to)

        courses = _COURSES if not region else [c for c in _COURSES if region in c["region"]]

        results = []
        current = start
        while current <= end:
            for course in courses:
                slots = self._available_slots(course["name"], current)
                if slots:
                    results.append({
                        "name":            course["name"],
                        "region":          course["region"],
                        "date":            current.isoformat(),
                        "available_slots": len(slots),
                        "tee_times":       slots,
                        "price_range":     course["price"],
                    })
            current += timedelta(days=1)

        return {
            "type": "golf_slots",
            "data": {
                "date_from":    date_from,
                "date_to":      date_to,
                "query_time":   today.isoformat(),
                "courses":      results,
            },
        }

    def _available_slots(self, course_name: str, target: date) -> list[str]:
        rng = random.Random(hash(course_name) + target.toordinal())
        is_weekend = target.weekday() >= 5

        # weekends: fewer slots (high demand), weekdays: more slots
        if is_weekend:
            count = rng.choices([0, 1, 2, 3], weights=[3, 4, 2, 1])[0]
        else:
            count = rng.choices([0, 2, 4, 6, 8], weights=[2, 2, 3, 2, 1])[0]

        return sorted(rng.sample(_TEE_SLOTS, min(count, len(_TEE_SLOTS))))
