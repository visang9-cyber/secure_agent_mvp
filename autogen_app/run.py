"""CLI 러너 — AutoGen 팀을 터미널에서 직접 실행합니다.

사용법:
    python -m autogen_app.run "이번 주말 날씨랑 골프장 추천해줘"
    python -m autogen_app.run --export   # gallery.json 내보내기
"""

import asyncio
import sys

# Windows cp949 터미널에서 이모지 출력 시 UnicodeEncodeError 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp949", "cp1252", "ascii"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from autogen_agentchat.ui import Console
from autogen_core import CancellationToken


def main() -> None:
    args = sys.argv[1:]

    if "--export" in args:
        from autogen_app.team import export_gallery
        export_gallery()
        return

    message = " ".join(args) if args else "이번 주말 날씨랑 골프장 추천해줘"

    async def _run() -> None:
        from autogen_app.team import create_team
        team = create_team()
        print(f"\n{'='*62}")
        print("🤖  Secure Agent MVP — AutoGen SelectorGroupChat")
        print(f"{'='*62}")
        print(f"질문: {message}\n")
        await Console(
            team.run_stream(task=message, cancellation_token=CancellationToken())
        )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
