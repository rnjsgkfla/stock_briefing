# Morning Bell

한국·미국 주식 투자자가 아침에 밤사이 미국 시장, 보유 종목 영향, 관심 종목 뉴스를 한
화면에서 확인하는 Python 기반 AI 브리핑 서비스입니다. 미국주식 투자자에게는 자는 동안
발생한 이슈를, 한국주식 투자자에게는 당일 국내장 시가에 영향을 줄 미국 시장과 환율·업종
이슈를 요약하는 것이 핵심입니다. 주문 기능과 매수·매도 추천은 포함하지 않습니다.

현재 MVP는 토스증권 Open API를 연결하면 한국·미국 관심 종목의 현재가를 조회합니다.
키가 없을 때도 포트폴리오를 실행해볼 수 있도록 샘플 데이터 모드를 함께 제공합니다.

## 현재 구현

- FastAPI 기반 REST API와 반응형 대시보드
- 사용자·종목·관심종목 SQLAlchemy 모델 및 영속 CRUD
- 시장/포트폴리오 브리핑 API와 프론트엔드 동적 렌더링
- 미국장·국장 상태, KOSPI/KOSDAQ 지수 및 국장·미장 분리 포트폴리오
- 뉴스·지수·관련 종목 근거를 펼쳐보는 오늘의 포커스 상세 보기
- Gemini 기반 실제 뉴스 카테고리 분류와 한국어 일괄 요약
- 관심 종목 기반 뉴스 수집, 중복 제거, 영속 저장 및 최신 이슈 피드
- 실제 뉴스와 샘플 분리, 기사 상세 모달 및 원문 출처 링크
- 토스증권 OAuth 토큰 캐시, 계좌 목록 조회 및 관심 종목 현재가 조회
- SQLite 로컬 실행, PostgreSQL/Redis/Celery Docker 환경
- Alembic 마이그레이션, pytest API 테스트, GitHub Actions CI

## 데이터 출처 현황

- 미국 10년물 금리: FRED `DGS10`, 원·달러 환율: 토스증권 Open API
- 포트폴리오 구성과 KOSPI/KOSDAQ 카드: 현재 샘플 데이터
- 관심 종목 가격: 기본 샘플 데이터, 선택적으로 토스증권 Open API
- 뉴스 피드: 기본 Mock 수집기, 선택적으로 Alpha Vantage `NEWS_SENTIMENT`
- AI 처리: 설정 시 Gemini가 수집된 실제 뉴스를 카테고리별 한국어로 요약
- Celery 아침 배치: 오전 7시 10분 뉴스 수집, 오전 7시 30분 브리핑 생성 스케줄

기본 설정의 숫자와 뉴스는 데모용 샘플입니다. `NEWS_PROVIDER=alpha_vantage`를 설정하면
뉴스 피드는 Alpha Vantage에서, `MARKET_DATA_PROVIDER=toss`를 설정하면 관심 종목 현재가는
토스증권에서 조회합니다.

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

최초 실행 시 데모 사용자와 `TSLA`, `AMD` 관심 종목이 생성됩니다. 토스증권 provider에서는
토스증권이 조회할 수 있는 국내 종목 코드와 미국 티커를 추가할 수 있으며, 등록 전에 종목
정보와 현재가를 실제 API로 검증합니다. 대표 국내 종목은 이름으로도 입력할 수 있습니다.

## 주요 API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/health` | 서버와 AI provider 상태 |
| GET | `/api/v1/dashboard` | 시장·포트폴리오·오늘의 포커스 |
| GET | `/api/v1/watchlist` | 관심 종목 조회 |
| POST | `/api/v1/watchlist` | 관심 종목 추가 |
| DELETE | `/api/v1/watchlist/{symbol}` | 관심 종목 삭제 |
| GET | `/api/v1/broker/accounts` | 토스증권 계좌 식별자 목록 조회 |
| GET | `/api/v1/news/latest` | 저장된 최신 뉴스 조회 |
| POST | `/api/v1/news/refresh` | 관심 종목 뉴스 수집 및 중복 제거 |
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
GEMINI_MODEL=gemini-3.5-flash-lite
```

무료 Gemini API에는 개인정보나 금융정보를 전달하지 않습니다. 보유 수량, 평균단가,
계좌 식별자와 증권사 인증정보는 프롬프트에 포함하면 안 됩니다.

## Alpha Vantage 뉴스 연결

```dotenv
NEWS_PROVIDER=alpha_vantage
ALPHA_VANTAGE_API_KEY=your-key
```

키가 없으면 `NEWS_PROVIDER=mock`을 유지합니다. Alpha Vantage의 무료 호출량이 제한적이므로
페이지 조회가 아니라 Celery 배치에서 수집하고 DB 결과를 재사용합니다.

## 토스증권 시세 연결

토스증권 앱에서 Open API 키와 허용 IP를 설정한 뒤 `.env`를 수정합니다.

```dotenv
MARKET_DATA_PROVIDER=toss
TOSS_INVEST_BASE_URL=https://openapi.tossinvest.com
TOSS_INVEST_CLIENT_ID=발급받은-client-id
TOSS_INVEST_CLIENT_SECRET=발급받은-client-secret
TOSS_INVEST_ACCOUNT=
```

서버를 실행한 뒤 `GET /api/v1/broker/accounts`의 `account_seq` 값을
`TOSS_INVEST_ACCOUNT`에 넣습니다. 현재 구현의 시세 조회에는 계좌 식별자가 필요하지 않으며,
향후 보유 자산 조회에서 사용합니다. 인증정보와 액세스 토큰은 DB나 로그에 저장하지 않습니다.

## Docker 실행

Docker 환경은 PostgreSQL, Redis, API, Celery worker, 뉴스·브리핑 배치 스케줄러를 함께
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
