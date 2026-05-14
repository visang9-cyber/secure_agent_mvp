# Secure Agent MVP

Multi-Agent Framework (MAF) + FastAPI 기반의 보안 에이전트 MVP.

## 프로젝트 구조

```
secure_agent_mvp/
├── app/
│   ├── agents/          # MAF 에이전트
│   ├── api/             # FastAPI 라우터
│   ├── core/            # 설정 및 공통 모듈
│   └── main.py          # FastAPI 앱 진입점
├── .env                 # 환경 변수 (git 제외)
├── .env.example         # 환경 변수 템플릿
├── requirements.txt
└── README.md
```

## 설치 및 실행

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 서버 실행
uvicorn app.main:app --reload
```

## API

- `GET /` — 서버 상태
- `GET /api/v1/health` — 헬스체크
