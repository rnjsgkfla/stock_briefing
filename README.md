# Morning Bell

한국·미국 주식 투자자가 아침에 밤사이 미국 시장, 보유 종목 영향, 관심 종목 뉴스를 한
화면에서 확인하는 Python 기반 AI 브리핑 서비스입니다. 미국주식 투자자에게는 자는 동안
발생한 이슈를, 한국주식 투자자에게는 당일 국내장 시가에 영향을 줄 미국 시장과 환율·업종
이슈를 요약하는 것이 핵심입니다. 주문 기능과 매수·매도 추천은 포함하지 않습니다.

현재 MVP의 종목·시세 샘플은 미국 종목만 지원합니다. 국내 종목과 KOSPI/KOSDAQ 데이터
연결은 다음 구현 범위이며, 제품의 최종 대상은 미국주식 전용이 아닙니다.

## 현재 구현

- FastAPI 기반 REST API와 반응형 대시보드
- 사용자·종목·관심종목 SQLAlchemy 모델 및 영속 CRUD
- 시장/포트폴리오 브리핑 API와 프론트엔드 동적 렌더링
- 공개 뉴스의 사실·해석·불확실성을 분리하는 Mock/Gemini 분석
- SQLite 로컬 실행, PostgreSQL/Redis/Celery Docker 환경
- Alembic 마이그레이션, pytest API 테스트, GitHub Actions CI

## 데이터 출처 현황

현재 외부 뉴스나 시세를 자동 수집하지 않습니다.

- 시장 지표, 포트폴리오 영향, 관심 종목 가격: `MarketDataService`의 샘플 데이터
- 뉴스 분석: 사용자가 화면에 입력한 제목과 본문을 `/api/v1/news/analyze`로 전달
- AI 처리: 기본은 Mock 응답이며, 설정 시 Gemini가 입력된 공개 뉴스를 구조화 분석
- Celery 아침 배치: 스케줄만 구성되어 있고 수집기 연결 전이라 작업을 건너뜀

따라서 현재 화면의 숫자와 뉴스는 Investing.com, Alpha Vantage, Yahoo Finance에서 가져온
실시간 데이터가 아닙니다.

상세 설계와 개발 범위는 [Architecture](docs/ARCHITECTURE.md),
[Roadmap](docs/ROADMAP.md)에서 확인할 수 있습니다.

## 빠른 실행

Python 3.12 이상이 필요합니다. 기본 설정은 SQLite와 Mock AI를 사용하므로 외부 서비스나
API 키 없이 동작합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

- 대시보드: <http://localhost:8000>
- API 문서: <http://localhost:8000/docs>
- 상태 확인: <http://localhost:8000/api/v1/health>

최초 실행 시 데모 사용자와 `TSLA`, `AMD` 관심 종목이 생성됩니다. 현재 샘플 시세를 제공하는
종목은 `AAPL`, `AMD`, `AMZN`, `GOOGL`, `META`, `MSFT`, `NVDA`, `TSLA`입니다.

## 주요 API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/health` | 서버와 AI provider 상태 |
| GET | `/api/v1/dashboard` | 시장·포트폴리오·오늘의 포커스 |
| GET | `/api/v1/watchlist` | 관심 종목 조회 |
| POST | `/api/v1/watchlist` | 관심 종목 추가 |
| DELETE | `/api/v1/watchlist/{symbol}` | 관심 종목 삭제 |
| POST | `/api/v1/news/analyze` | 공개 뉴스 구조화 분석 |

관심 종목 추가 예시:

```bash
curl -X POST http://localhost:8000/api/v1/watchlist \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"NVDA"}'
```

## Gemini 연결

Google AI Studio에서 키를 발급한 뒤 `.env`를 수정합니다.

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.7-flash
```

무료 Gemini API에는 개인정보나 금융정보를 전달하지 않습니다. 보유 수량, 평균단가,
계좌 식별자와 증권사 인증정보는 프롬프트에 포함하면 안 됩니다.

## Docker 실행

Docker 환경은 PostgreSQL, Redis, API, Celery worker, 오전 7시 30분 배치 스케줄러를 함께
실행합니다.

```bash
cp .env.example .env
docker compose up --build
```

## DB 마이그레이션

새 DB 스키마를 생성하거나 갱신할 때 실행합니다.

```bash
alembic upgrade head
```

로컬 앱은 데모 편의를 위해 누락된 테이블을 시작 시 자동 생성합니다. 실제 배포에서는
마이그레이션을 배포 단계에서 먼저 수행하도록 분리하는 것이 다음 목표입니다.

## 품질 확인

```bash
ruff check .
pytest -q
```

테스트는 메모리 SQLite를 사용하므로 로컬 DB를 변경하지 않습니다.
