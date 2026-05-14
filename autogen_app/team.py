"""AutoGen 팀 정의 — SelectorGroupChat 기반 멀티에이전트."""

import json
from datetime import date

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_app.tools import (
    get_golf_recommendations,
    get_golf_slots,
    get_my_schedule,
    get_weather,
)
from app.core.config import settings

# ── Selector 프롬프트 ─────────────────────────────────────────────────────────
_SELECTOR_PROMPT = """다음 대화를 보고 다음 발언자를 한 명 선택하세요.

에이전트 역할:
- super_agent : 오케스트레이터. 사용자 메시지 분석 및 최종 요약 답변
- weather_agent : 날씨/기온/예보 조회 전담
- golf_agent : 수도권 골프장 예약 현황 조회 전담
- schedule_agent : 사용자 일정 조회 전담 (Mock MSA)
- planner_agent : 날씨+골프+일정 복합 TOP 5 추천 전담 (복합 요청 시)

선택 규칙:
1. 사용자의 첫 메시지 → super_agent
2. super_agent가 단일 도메인 요청 확인 → 해당 전문 에이전트
3. super_agent가 2개+ 도메인 복합 요청 확인 → planner_agent
4. 전문 에이전트 결과 반환 후 → super_agent (최종 답변)
5. super_agent가 TERMINATE 발화 → 종료

대화 기록:
{history}

다음 발언자(에이전트 이름만):"""


def _make_client() -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    )


def create_team() -> SelectorGroupChat:
    client = _make_client()
    today = date.today().isoformat()

    weather_agent = AssistantAgent(
        name="weather_agent",
        description="날씨/기온/예보/우산 관련 질문 전담 에이전트",
        model_client=client,
        tools=[get_weather],
        system_message=(
            f"오늘 날짜: {today}. "
            "당신은 날씨 정보 전문 에이전트입니다. "
            "'이번 달', '이번 주' 등 상대적 표현은 오늘 날짜 기준으로 해석하세요. "
            "get_weather 도구로 날씨를 조회한 뒤 결과를 간결하게 정리해 주세요. "
            "추가 행동 없이 결과만 반환하세요."
        ),
    )

    golf_agent = AssistantAgent(
        name="golf_agent",
        description="수도권 골프장 예약·티타임·가용 슬롯 조회 전담 에이전트",
        model_client=client,
        tools=[get_golf_slots],
        system_message=(
            f"오늘 날짜: {today}. "
            "당신은 골프장 예약 현황 전문 에이전트입니다. "
            "'이번 주말', '다음 주' 등 상대적 표현은 오늘 날짜 기준으로 해석하세요. "
            "get_golf_slots 도구로 예약 가능 슬롯을 조회하고 결과를 반환하세요."
        ),
    )

    schedule_agent = AssistantAgent(
        name="schedule_agent",
        description="사용자 일정·약속·회의·스케줄 조회 전담 에이전트 (Mock MSA)",
        model_client=client,
        tools=[get_my_schedule],
        system_message=(
            f"오늘 날짜: {today}. "
            "당신은 일정 관리 전문 에이전트입니다. "
            "'이번 주', '이번 달' 등 상대적 표현은 오늘 날짜 기준으로 해석하세요. "
            "get_my_schedule 도구로 사용자 일정을 조회하고 결과를 반환하세요."
        ),
    )

    planner_agent = AssistantAgent(
        name="planner_agent",
        description="날씨·골프장·일정을 종합 분석해 최적 골프 라운드 TOP 5를 추천하는 에이전트",
        model_client=client,
        tools=[get_golf_recommendations],
        system_message=(
            f"오늘 날짜: {today}. "
            "당신은 골프 라운드 추천 전문 에이전트입니다. "
            "'이번 주말', '다음 달' 등 상대적 표현은 오늘 날짜 기준으로 해석하세요. "
            "get_golf_recommendations 도구로 날씨·골프장·일정을 종합 분석해 TOP 5를 추천하세요."
        ),
    )

    super_agent = AssistantAgent(
        name="super_agent",
        description="사용자 의도 파악 및 서브에이전트 조율 오케스트레이터",
        model_client=client,
        system_message=f"""오늘 날짜: {today}.
당신은 멀티에이전트 팀의 오케스트레이터(SuperAgent)입니다.

서브에이전트:
- weather_agent  : 날씨 조회
- golf_agent     : 골프장 예약 현황
- schedule_agent : 내 일정 조회
- planner_agent  : 2개 이상 도메인 복합 분석 및 TOP 5 추천

역할:
1. 사용자 메시지를 분석해 필요한 에이전트를 파악합니다. '이번 달', '이번 주말' 등은 오늘 날짜 기준으로 해석하세요.
2. 서브에이전트 결과를 받아 사용자에게 자연스러운 한국어로 최종 요약을 제공합니다.
3. 답변 완료 후 반드시 마지막에 "TERMINATE"를 출력해 세션을 종료합니다.""",
    )

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(15)

    return SelectorGroupChat(
        participants=[super_agent, weather_agent, golf_agent, schedule_agent, planner_agent],
        model_client=client,
        termination_condition=termination,
        selector_prompt=_SELECTOR_PROMPT,
    )


def export_gallery(path: str = "autogen_app/gallery.json") -> None:
    """AutoGen Studio에 임포트할 갤러리 JSON을 생성합니다."""
    team = create_team()
    config = team.dump_component()
    gallery = {
        "version": "1.0.0",
        "components": {"teams": [config.model_dump()]},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gallery, f, ensure_ascii=False, indent=2, default=str)
    print(f"gallery.json saved: {path}")
