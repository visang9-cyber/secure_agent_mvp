"""AutoGen tool functions — 기존 에이전트 로직을 AutoGen callable로 래핑."""

import os
import sys

# AutoGen Studio가 다른 CWD에서 툴 소스코드를 재실행할 때도
# app.* 패키지를 찾을 수 있도록 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from datetime import date, timedelta


async def get_weather(year: int, month: int, location: str = "서울") -> str:
    """서울 등 도시의 월별 날씨 예보를 조회합니다.

    Args:
        year: 연도 (예: 2026)
        month: 월 (1-12)
        location: 도시명 (기본값: 서울)
    """
    from app.agents.weather_agent import WeatherAgent
    result = await WeatherAgent().run(year=year, month=month, location=location)
    data = result["data"]
    lines = [f"📅 {data['year']}년 {data['month']}월 날씨 ({data['location']})"]
    for day in data["days"]:
        lines.append(
            f"  {day['date']}: {day['icon']} {day['min_temp']}°~{day['max_temp']}° ({day['condition']})"
        )
    return "\n".join(lines)


async def get_golf_slots(date_from: str, date_to: str, region: str = "") -> str:
    """수도권 골프장의 일자별 예약 가능 슬롯을 조회합니다.

    Args:
        date_from: 시작일 YYYY-MM-DD
        date_to: 종료일 YYYY-MM-DD
        region: 지역 필터 (선택, 예: 용인시)
    """
    from app.agents.golf_agent import GolfAgent
    result = await GolfAgent().run(date_from=date_from, date_to=date_to, region=region)
    courses = result["data"]["courses"]
    if not courses:
        return f"예약 가능한 슬롯이 없습니다 ({date_from} ~ {date_to})."
    lines = [f"⛳ 골프장 예약 현황 ({date_from} ~ {date_to})"]
    for c in courses[:15]:
        times = ", ".join(c["tee_times"])
        lines.append(
            f"  {c['date']} | {c['name']} ({c['region']}) | "
            f"{c['available_slots']}타임 [{times}] | {c['price_range']}"
        )
    return "\n".join(lines)


async def get_my_schedule(date_from: str, date_to: str) -> str:
    """사용자의 일정을 조회합니다 (Mock MSA, seed=42 고정).

    Args:
        date_from: 시작일 YYYY-MM-DD
        date_to: 종료일 YYYY-MM-DD
    """
    from app.api.mock_schedule import _generate_day
    from app.core.config import settings

    start = date.fromisoformat(date_from)
    end   = date.fromisoformat(date_to)
    lines = [f"📅 내 일정 ({date_from} ~ {date_to})"]
    current = start
    while current <= end:
        events = _generate_day(current, settings.schedule_seed)
        if events:
            lines.append(f"\n  [{current.isoformat()}]")
            for e in events:
                lines.append(f"    {e['time']} {e['title']}")
        else:
            lines.append(f"\n  [{current.isoformat()}] 일정 없음")
        current += timedelta(days=1)
    return "\n".join(lines)


async def get_golf_recommendations(
    date_from: str,
    date_to: str,
    location: str = "서울",
    include_schedule: bool = True,
) -> str:
    """날씨·골프장·일정을 종합 분석해 최적 골프 라운드 TOP 5를 추천합니다.

    Args:
        date_from: 시작일 YYYY-MM-DD
        date_to: 종료일 YYYY-MM-DD
        location: 기준 도시 (기본값: 서울)
        include_schedule: 내 일정 충돌 고려 여부 (기본값: True)
    """
    from app.agents.planner_agent import PlannerAgent
    intents = ["weather", "golf"] + (["schedule"] if include_schedule else [])
    result = await PlannerAgent().run(
        intents=intents, date_from=date_from, date_to=date_to, location=location
    )
    data = result["data"]
    recs  = data.get("recommendations", [])
    if not recs:
        return "추천 가능한 라운드가 없습니다. 날짜 범위를 넓혀 보세요."
    lines = [
        f"🏆 골프 라운드 TOP {len(recs)} 추천 ({date_from} ~ {date_to})",
        f"채점 기준: {data['criteria']}",
        "",
    ]
    for r in recs:
        lines.append(
            f"  #{r['rank']} {r['date']}({r['weekday']}) {r['course_name']} | "
            f"{r['weather_icon']} {r['weather_temp']} | {r['schedule_label']} | "
            f"추천티타임: {r['best_tee_time']} | {r['price_range']} | 점수: {r['score']}"
        )
        lines.append(f"       예약링크: {r['link']}")
    return "\n".join(lines)
