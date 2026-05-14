from datetime import date, timedelta

import httpx

from app.agents.base_agent import BaseAgent
from app.core.config import settings


class ScheduleAgent(BaseAgent):
    def __init__(self):
        super().__init__("ScheduleAgent")

    async def run(self, **kwargs) -> dict:
        today = date.today()
        date_from: str = kwargs.get("date_from", today.isoformat())
        date_to: str   = kwargs.get("date_to",   (today + timedelta(days=6)).isoformat())

        url = f"{settings.schedule_msa_url}/mock/schedule"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"date_from": date_from, "date_to": date_to})
            resp.raise_for_status()
            payload = resp.json()

        return {
            "type": "schedule_list",
            "data": {
                "date_from":  date_from,
                "date_to":    date_to,
                "schedules":  payload["schedules"],
            },
        }
