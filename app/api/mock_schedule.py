import random
from datetime import date, timedelta

from fastapi import APIRouter, Query

router = APIRouter()

_WEEKDAY_POOL = [
    {"time": "09:00", "title": "팀 스탠드업"},
    {"time": "10:00", "title": "주간 회의"},
    {"time": "11:00", "title": "1:1 면담"},
    {"time": "14:00", "title": "코드 리뷰"},
    {"time": "12:00", "title": "점심 약속"},
    {"time": "15:00", "title": "외부 미팅"},
    {"time": "16:00", "title": "클라이언트 콜"},
    {"time": "17:00", "title": "기획 리뷰"},
    {"time": "13:00", "title": "제품 데모"},
]

_WEEKEND_POOL = [
    {"time": "07:30", "title": "골프 라운드"},
    {"time": "10:00", "title": "가족 행사"},
    {"time": "11:00", "title": "개인 운동"},
    {"time": "14:00", "title": "병원 예약"},
    {"time": "15:00", "title": "친구 약속"},
    {"time": "18:00", "title": "저녁 약속"},
    {"time": "09:00", "title": "등산"},
]


def _generate_day(target: date, seed: int) -> list[dict]:
    rng = random.Random(seed + target.toordinal())
    is_weekend = target.weekday() >= 5

    if is_weekend:
        count = rng.choices([0, 2, 3, 4], weights=[1, 3, 3, 1])[0]
        pool = _WEEKEND_POOL
    else:
        count = rng.choices([0, 3, 4, 5], weights=[1, 3, 3, 1])[0]
        pool = _WEEKDAY_POOL

    selected = rng.sample(pool, min(count, len(pool)))
    return sorted(selected, key=lambda x: x["time"])


@router.get("/mock/schedule")
async def get_schedule(
    date_from: str = Query(...),
    date_to: str = Query(...),
):
    from app.core.config import settings

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)

    schedules: dict[str, list] = {}
    current = start
    while current <= end:
        schedules[current.isoformat()] = _generate_day(current, settings.schedule_seed)
        current += timedelta(days=1)

    return {"schedules": schedules}
