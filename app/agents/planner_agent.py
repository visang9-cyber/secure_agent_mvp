"""
PlannerAgent (SubAgent#4)

2개 이상의 인텐트가 감지될 때 SuperAgent가 호출.
날씨 · 골프장 가용성 · 내 일정 충돌을 종합 채점해 TOP 5를 반환.

scoring
  weather_score  : clear=10, partly_cloudy=8, cloudy=4, rain=0, heavy_rain=-5, snow=1
  avail_score    : min(slots × 1.2, 10)
  schedule_penalty: 종일=-8, 오전=-3, 오후=-2, 저녁전용=+1, 없음=0
  weekend_bonus  : +4
  ※ weather_score < 0 인 날(폭우)은 후보 제외
"""

import asyncio
import urllib.parse
from datetime import date, timedelta

from app.agents.base_agent import BaseAgent

_WEATHER_SCORE = {
    "clear":         10,
    "partly_cloudy":  8,
    "cloudy":         4,
    "rain":           0,
    "heavy_rain":    -5,
    "snow":           1,
}

_WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

_COURSE_URLS: dict[str, str] = {
    "파주 CC":        "https://search.naver.com/search.naver?query=파주CC+골프장+예약",
    "베어크릭 GC":    "https://search.naver.com/search.naver?query=베어크릭GC+예약",
    "88 CC":          "https://search.naver.com/search.naver?query=88CC+용인+골프예약",
    "레이크사이드 CC":"https://search.naver.com/search.naver?query=레이크사이드CC+예약",
    "기흥 CC":        "https://search.naver.com/search.naver?query=기흥CC+골프예약",
    "그린밸리 CC":    "https://search.naver.com/search.naver?query=그린밸리CC+예약",
    "남촌 CC":        "https://search.naver.com/search.naver?query=남촌CC+골프예약",
    "엘리시안 강촌":  "https://search.naver.com/search.naver?query=엘리시안강촌+골프예약",
    "비전힐스 CC":    "https://search.naver.com/search.naver?query=비전힐스CC+예약",
    "클럽 900":       "https://search.naver.com/search.naver?query=클럽900+양주+골프예약",
    "한양 CC":        "https://search.naver.com/search.naver?query=한양CC+양주+예약",
    "포천 힐스 CC":   "https://search.naver.com/search.naver?query=포천힐스CC+예약",
}


def _course_link(name: str) -> str:
    return _COURSE_URLS.get(
        name,
        "https://search.naver.com/search.naver?query="
        + urllib.parse.quote(name + " 골프예약"),
    )


def _schedule_info(events) -> tuple[int, str]:
    if events is None:
        return 0, "미조회"
    if not events:
        return 0, "일정 없음 ✅"
    morning   = [e for e in events if e["time"] < "12:00"]
    afternoon = [e for e in events if "12:00" <= e["time"] < "18:00"]
    if morning and afternoon:
        return -8, f"종일 바쁨 ({len(events)}건)"
    if morning:
        return -3, f"오전 일정 ({len(morning)}건)"
    if afternoon:
        return -2, f"오후 일정 ({len(afternoon)}건)"
    return 1, f"저녁 일정만 ({len(events)}건) ✅"


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("PlannerAgent")

    async def run(self, **kwargs) -> dict:
        from app.agents.golf_agent import GolfAgent
        from app.agents.schedule_agent import ScheduleAgent
        from app.agents.weather_agent import WeatherAgent

        intents  = kwargs.get("intents", ["weather", "golf"])
        today    = date.today()

        date_from = kwargs.get("date_from") or (today + timedelta(days=1)).isoformat()
        date_to   = kwargs.get("date_to")   or (today + timedelta(days=14)).isoformat()
        location  = kwargs.get("location", "서울")

        start = date.fromisoformat(date_from)
        end   = date.fromisoformat(date_to)

        # 날씨는 날짜 범위에 걸친 월 단위로 가져옴
        months: set[tuple[int, int]] = set()
        cur = start.replace(day=1)
        while cur <= end:
            months.add((cur.year, cur.month))
            cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)

        golf_task     = asyncio.create_task(GolfAgent().run(date_from=date_from, date_to=date_to))
        weather_tasks = [
            asyncio.create_task(WeatherAgent().run(year=y, month=m, location=location))
            for y, m in sorted(months)
        ]
        use_schedule  = "schedule" in intents
        sched_task    = asyncio.create_task(
            ScheduleAgent().run(date_from=date_from, date_to=date_to)
        ) if use_schedule else None

        all_tasks = [golf_task, *weather_tasks] + ([sched_task] if sched_task else [])
        results   = await asyncio.gather(*all_tasks, return_exceptions=True)

        golf_result    = results[0] if not isinstance(results[0], Exception) else None
        weather_results = [r for r in results[1 : 1 + len(weather_tasks)]
                           if not isinstance(r, Exception)]
        sched_result   = results[-1] if (sched_task and not isinstance(results[-1], Exception)) else None

        # 날짜 → 날씨 lookup
        weather_lookup: dict[str, dict] = {}
        for wr in weather_results:
            for day in wr.get("data", {}).get("days", []):
                weather_lookup[day["date"]] = day

        # 날짜 → 일정 lookup
        schedule_lookup: dict[str, list] = {}
        if sched_result:
            schedule_lookup = sched_result.get("data", {}).get("schedules", {})

        recommendations = self._rank(
            golf_result["data"] if golf_result else {},
            weather_lookup,
            schedule_lookup,
            use_schedule,
        )

        return {
            "type": "recommendation",
            "data": {
                "date_from":       date_from,
                "date_to":         date_to,
                "criteria":        self._criteria_label(intents),
                "recommendations": recommendations,
            },
        }

    def _rank(self, golf_data, weather_lookup, schedule_lookup, use_schedule):
        candidates = []
        for course in golf_data.get("courses", []):
            date_str   = course["date"]
            dt         = date.fromisoformat(date_str)
            is_weekend = dt.weekday() >= 5

            w_day   = weather_lookup.get(date_str, {})
            w_score = _WEATHER_SCORE.get(w_day.get("condition", "partly_cloudy"), 4)
            if w_score < 0:
                continue  # 폭우 제외

            w_icon = w_day.get("icon", "⛅")
            w_temp = (f"{w_day['min_temp']}°~{w_day['max_temp']}°" if w_day else "-")

            avail_score   = min(course["available_slots"] * 1.2, 10)
            weekend_bonus = 4 if is_weekend else 0

            events   = schedule_lookup.get(date_str) if use_schedule else None
            s_pen, s_label = _schedule_info(events)

            total = w_score + avail_score + s_pen + weekend_bonus

            candidates.append({
                "date":            date_str,
                "weekday":         _WEEKDAY_KR[dt.weekday()],
                "is_weekend":      is_weekend,
                "course_name":     course["name"],
                "region":          course["region"],
                "price_range":     course["price_range"],
                "weather_icon":    w_icon,
                "weather_temp":    w_temp,
                "available_slots": course["available_slots"],
                "best_tee_time":   course["tee_times"][0] if course["tee_times"] else "-",
                "schedule_label":  s_label,
                "score":           round(total, 1),
                "link":            _course_link(course["name"]),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        for i, c in enumerate(candidates):
            c["rank"] = i + 1
        return candidates[:5]

    @staticmethod
    def _criteria_label(intents: list[str]) -> str:
        parts = []
        if "weather"  in intents: parts.append("날씨 ☀️ ×1.0")
        if "golf"     in intents: parts.append("가용슬롯 ⛳ ×1.2")
        if "schedule" in intents: parts.append("일정충돌 📅")
        parts.append("주말 +4")
        return "  ·  ".join(parts)
