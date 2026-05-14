import asyncio
import json
import re
from datetime import date, timedelta

from app.agents.base_agent import BaseAgent
from app.agents.golf_agent import GolfAgent
from app.agents.schedule_agent import ScheduleAgent
from app.agents.weather_agent import WeatherAgent
from app.core.config import settings

_weather_agent  = WeatherAgent()
_golf_agent     = GolfAgent()
_schedule_agent = ScheduleAgent()

_KEYWORD_MAP = {
    "weather":  ["날씨", "기온", "비", "눈", "흐림", "맑음", "예보", "기상", "우산"],
    "golf":     ["골프", "골프장", "티타임", "라운드", "예약"],
    "schedule": ["일정", "스케줄", "캘린더", "약속", "회의", "미팅", "할 일"],
}


# ── date helpers ─────────────────────────────────────────────────────────────

def _this_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _extract_params(msg: str) -> dict:
    today = date.today()
    params: dict = {}

    month_m = re.search(r"(\d{1,2})월", msg)
    if "이번 달" in msg or "이번달" in msg:
        params["year"] = today.year
        params["month"] = today.month
    elif "다음 달" in msg or "다음달" in msg:
        nxt = today.replace(day=1) + timedelta(days=32)
        params["year"] = nxt.year
        params["month"] = nxt.month
    elif month_m:
        params["year"] = today.year
        params["month"] = int(month_m.group(1))

    if "오늘" in msg:
        params["date_from"] = params["date_to"] = today.isoformat()
    elif "내일" in msg:
        tomorrow = today + timedelta(days=1)
        params["date_from"] = params["date_to"] = tomorrow.isoformat()
    elif "이번 주말" in msg or "이번주말" in msg:
        mon = _this_monday()
        params["date_from"] = (mon + timedelta(days=5)).isoformat()
        params["date_to"]   = (mon + timedelta(days=6)).isoformat()
    elif "이번 주" in msg or "이번주" in msg:
        mon = _this_monday()
        params["date_from"] = mon.isoformat()
        params["date_to"]   = (mon + timedelta(days=6)).isoformat()
    elif "다음 주" in msg or "다음주" in msg:
        mon = _this_monday() + timedelta(weeks=1)
        params["date_from"] = mon.isoformat()
        params["date_to"]   = (mon + timedelta(days=6)).isoformat()

    if "location" not in params:
        for city in ["서울", "경기", "인천", "파주", "용인", "수원", "광주", "가평", "이천", "포천", "양주"]:
            if city in msg:
                params["location"] = city
                params["region"] = city
                break

    return params


def _keyword_classify(msg: str) -> list[str]:
    intents = []
    for intent, keywords in _KEYWORD_MAP.items():
        if any(kw in msg for kw in keywords):
            intents.append(intent)
    return intents or ["general"]


async def _llm_classify(msg: str) -> tuple[list[str], dict]:
    """OpenAI로 의도 + 파라미터 추출. API 키 없으면 키워드 분류로 대체."""
    key = settings.openai_api_key
    if not key or key.startswith("your_"):
        return _keyword_classify(msg), _extract_params(msg)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    today = date.today().isoformat()

    system = f"""오늘 날짜: {today}
사용자 메시지에서 의도와 날짜 파라미터를 추출해 아래 JSON으로만 응답하세요.
{{
  "intents": ["weather"|"golf"|"schedule"],   // 해당하는 것만, 없으면 []
  "params": {{
    "year": <int|null>,
    "month": <int|null>,
    "date_from": "<YYYY-MM-DD>|null",
    "date_to": "<YYYY-MM-DD>|null",
    "location": "<string|null>",
    "region": "<string|null>"
  }}
}}
intents에 들어갈 수 있는 값: weather, golf, schedule (복수 가능)"""

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": msg}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    parsed = json.loads(resp.choices[0].message.content)
    intents = parsed.get("intents") or _keyword_classify(msg)
    raw_params = parsed.get("params", {})
    params = {k: v for k, v in raw_params.items() if v is not None}

    if not params:
        params = _extract_params(msg)

    return intents, params


async def _generate_summary(msg: str, cards: list[dict]) -> str:
    key = settings.openai_api_key
    if not key or key.startswith("your_"):
        types = [c["type"] for c in cards]
        labels = {"weather_calendar": "날씨", "golf_slots": "골프장", "schedule_list": "일정"}
        names = [labels.get(t, t) for t in types]
        return f"{', '.join(names)} 정보를 조회했습니다. 아래 카드를 확인해 주세요." if names else "죄송합니다, 관련 정보를 찾을 수 없었습니다."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    card_summary = json.dumps(cards, ensure_ascii=False, default=str)[:2000]

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "아래 카드 데이터를 바탕으로 사용자 질문에 한국어로 2~3문장의 자연스러운 요약 답변을 작성하세요."},
            {"role": "user", "content": f"질문: {msg}\n\n카드 데이터: {card_summary}"},
        ],
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()


# ── SuperAgent ────────────────────────────────────────────────────────────────

class SuperAgent(BaseAgent):
    def __init__(self):
        super().__init__("SuperAgent")

    async def run(self, **kwargs) -> dict:
        message: str = kwargs.get("message", "")

        intents, params = await _llm_classify(message)

        agent_tasks = []
        if "weather" in intents:
            agent_tasks.append(_weather_agent.run(**params))
        if "golf" in intents:
            agent_tasks.append(_golf_agent.run(**params))
        if "schedule" in intents:
            agent_tasks.append(_schedule_agent.run(**params))

        if not agent_tasks:
            return {"text": "죄송합니다, 날씨 / 골프장 / 일정 관련 질문을 해 주세요.", "cards": []}

        results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        cards = [r for r in results if isinstance(r, dict)]
        errors = [str(r) for r in results if isinstance(r, Exception)]

        text = await _generate_summary(message, cards)
        if errors:
            text += f"\n\n⚠️ 일부 조회 실패: {'; '.join(errors)}"

        return {"text": text, "cards": cards}


super_agent = SuperAgent()
