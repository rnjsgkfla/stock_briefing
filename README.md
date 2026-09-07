# Morning Bell

한국·미국 주식 투자자를 위한 Python 기반 아침 시장 브리핑 서비스입니다.

미국 주식 투자자는 잠든 사이 발생한 미국장 이슈를 빠르게 확인하고, 국내 주식 투자자는
밤사이 미국 시장·금리·환율·반도체 흐름이 당일 국내장에 미칠 영향을 한 화면에서 파악할 수
있습니다. 이 프로젝트는 정보 탐색 시간을 줄이는 것이 목적이며 주문 실행, 종목 추천,
수익률 예측 기능은 제공하지 않습니다.

## 핵심 사용자 흐름

1. 사용자가 국내 종목 코드 또는 미국 티커를 관심 종목에 추가합니다.
2. 토스증권 Open API에서 종목 정보, 현재가, 전일 대비 등락률을 조회합니다.
3. Alpha Vantage에서 관심 종목 및 거시경제 관련 뉴스를 수집하고 중복을 제거합니다.
4. Gemini가 영문 기사를 한국어로 요약하고 금리·환율·반도체·실적·전쟁·지정학 등의
   카테고리로 분류합니다.
5. 현재가, 미국 10년물 금리, 원·달러 환율과 관련 뉴스를 결합해 오늘 확인할 항목을
   수치와 근거 기사로 보여줍니다.
6. 뉴스 카드를 누르면 한국어 요약과 관련 종목을 확인하고 원문 기사로 이동할 수 있습니다.

## 구현 상태

| 영역 | 현재 상태 | 데이터 출처 |
| --- | --- | --- |
| 관심 종목 | 국내 종목 코드·미국 티커 추가/조회/삭제 | Mock 또는 토스증권 Open API |
| 관심 종목 현재가 | 종목 추가 전 유효성 및 가격 확인, 전일 대비 등락률 표시 | 토스증권 가격·일봉 API |
| 오늘 확인할 3가지 | 반도체 평균 등락률, 미국 10년물, USD/KRW 수치와 관련 뉴스 근거 | 토스증권·FRED·저장 뉴스 |
| 밤사이 주요 이슈 | 실제 기사 수집, URL 기반 중복 제거, 카테고리별 표시 | Alpha Vantage `NEWS_SENTIMENT` |
| 뉴스 AI 처리 | 한국어 요약 및 카테고리 분류 | Gemini structured output |
| 뉴스 상세 | 한국어 요약, 관련 종목, 감성 정보, 원문 링크 | 저장된 뉴스 DB |
| 시장 상태 | 미국장·국장 상태 표시 | 국장은 한국 시간 기준 계산, 미국장은 현재 정적 표시 |
| 시장 지수 카드 | NASDAQ, S&P 500, KOSPI, KOSDAQ | 현재 샘플 데이터 |
| 국장·미장 포트폴리오 | 시장별 보유 비중 및 영향도 UI | 현재 샘플 데이터 |
| 계좌 연동 | 토스증권 계좌 식별자 목록 조회 | 토스증권 Open API |
| 배치 처리 | 07:10 뉴스 수집 동작, 07:30 브리핑 작업은 placeholder | Celery Beat·Redis |

대시보드의 `sample_data` 값이 `true`인 이유는 시장 지수와 포트폴리오 구성이 아직 샘플이기
때문입니다. 실제 provider를 설정하면 관심 종목 가격, 미국 10년물 금리, USD/KRW, 뉴스와
오늘의 포커스는 외부 데이터를 사용합니다.

## 기술 스택

- Backend: Python 3.12, FastAPI, Pydantic
- Database: SQLAlchemy Async, SQLite, PostgreSQL, Alembic
- AI: Google Gemini
- Market data: Toss Invest Open API, FRED `DGS10`
- News: Alpha Vantage `NEWS_SENTIMENT`
- Batch: Celery, Redis, Celery Beat
- Frontend: HTML, CSS, Vanilla JavaScript
- Quality: pytest, Ruff, GitHub Actions
- Local infrastructure: Docker Compose

## 구조

```text
Browser
  ├─ GET /api/v1/dashboard
  │    ├─ Toss: 반도체 종목 현재가, USD/KRW
  │    ├─ FRED: 미국 10년물 국채 금리
  │    └─ DB: 카테고리별 한국어 뉴스 근거
  ├─ CRUD /api/v1/watchlist
  │    └─ Toss: 종목 정보와 현재가 검증 → DB 저장
  └─ POST /api/v1/news/refresh
       └─ Alpha Vantage → 중복 제거 → Gemini 요약·분류 → DB 저장

Celery Beat → Redis → Celery Worker
```

세부 설계는 [Architecture](docs/ARCHITECTURE.md), 이후 개발 계획은
[Roadmap](docs/ROADMAP.md)에서 확인할 수 있습니다.

## 빠른 실행: API 키 없이 Mock 모드

Python 3.12 이상이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8765
```

- 대시보드: <http://127.0.0.1:8765>
- Swagger API 문서: <http://127.0.0.1:8765/docs>
- 상태 확인: <http://127.0.0.1:8765/api/v1/health>

최초 실행 시 데모 사용자와 기본 관심 종목이 생성됩니다. 기본 `.env.example`은 Mock
provider를 사용하므로 외부 계정이나 유료 API 없이 UI와 CRUD를 확인할 수 있습니다.

## 실제 데이터 연결

프로젝트 루트의 `.env`를 다음과 같이 설정합니다.

```dotenv
APP_ENV=local
DATABASE_URL=sqlite+aiosqlite:///./stock_briefing.db
REDIS_URL=redis://localhost:6379/0

AI_PROVIDER=gemini
GEMINI_API_KEY=발급받은-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite

NEWS_PROVIDER=alpha_vantage
ALPHA_VANTAGE_API_KEY=발급받은-alpha-vantage-api-key

MARKET_DATA_PROVIDER=toss
TOSS_INVEST_BASE_URL=https://openapi.tossinvest.com
TOSS_INVEST_CLIENT_ID=발급받은-client-id
TOSS_INVEST_CLIENT_SECRET=발급받은-client-secret
TOSS_INVEST_ACCOUNT=
```

키에 `_` 또는 `-`가 있어도 일반적으로 따옴표 없이 그대로 입력할 수 있습니다. 값에 공백,
`#` 또는 따옴표 자체가 포함될 때만 전체 값을 따옴표로 감싸세요. `.env`는 `.gitignore`에
포함되어 있으므로 Git에 커밋하지 않습니다.

설정을 바꾼 뒤 서버를 완전히 다시 시작해야 새 환경 변수가 적용됩니다.

### Gemini

[Google AI Studio](https://aistudio.google.com/)에서 API 키를 발급합니다. Gemini에는 공개
뉴스의 제목과 요약문만 전달하며 토스 Client Secret, 액세스 토큰, 계좌 식별자, 보유 수량과
평균단가는 전달하지 않습니다.

### Alpha Vantage

[Alpha Vantage](https://www.alphavantage.co/support/#api-key)에서 키를 발급합니다. 뉴스 수집
버튼 또는 배치 작업이 실제 API를 호출하며, 수집된 기사는 DB에 저장되어 페이지를 열 때마다
외부 API를 다시 호출하지 않습니다. provider 호출량을 아끼기 위해 URL 해시를 외부 ID로
사용하고 중복 기사는 다시 저장하지 않습니다.

### 토스증권 Open API

[토스증권 Open API 문서](https://developers.tossinvest.com/docs)를 참고해 Client ID, Client
Secret과 허용 IP를 설정합니다.

`TOSS_INVEST_ACCOUNT`는 토스증권 계좌 식별자인 `account_seq`를 넣는 자리입니다. 서버 실행
후 `GET /api/v1/broker/accounts`에서 조회할 수 있습니다. 현재 관심 종목의 종목 정보·현재가·
환율 조회에는 계좌 식별자가 필요하지 않으므로 비워두어도 됩니다. 향후 실제 보유 자산 조회
기능에서 사용할 예정입니다.

## API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/health` | 서버와 활성 provider 상태 |
| GET | `/api/v1/dashboard` | 시장 카드, 포트폴리오, 오늘의 포커스 |
| GET | `/api/v1/watchlist` | 관심 종목과 현재가 조회 |
| POST | `/api/v1/watchlist` | 종목 정보·현재가 확인 후 관심 종목 추가 |
| DELETE | `/api/v1/watchlist/{symbol}` | 관심 종목 삭제 |
| GET | `/api/v1/broker/accounts` | 토스증권 계좌 식별자 목록 조회 |
| GET | `/api/v1/news/latest` | 활성 provider의 최신 저장 뉴스 조회 |
| POST | `/api/v1/news/refresh` | 실제 뉴스 수집, 중복 제거, 한국어 요약·분류 |
| POST | `/api/v1/news/analyze` | 공개 뉴스 구조화 분석용 내부 API; 현재 UI에는 노출하지 않음 |

관심 종목 추가:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/watchlist \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"NVDA"}'
```

국내 종목은 `005930`과 같은 종목 코드를 입력합니다. Mock 모드에서는 프로젝트에 등록된
종목만 지원하며, Toss 모드에서는 토스증권 API가 조회할 수 있는 국내 종목 코드와 미국
티커를 추가할 수 있습니다. 일부 대표 국내 종목은 이름 입력도 지원합니다.

뉴스 수집:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/news/refresh
```

응답의 의미:

- `collected_count`: provider에서 이번 요청에 받은 기사 수
- `stored_count`: 중복이 아니어서 새로 저장한 기사 수
- `duplicate_count`: 이미 DB에 존재한 기사 수
- `summarized_count`: 이번 요청에서 Gemini 또는 Mock AI가 요약·분류한 기사 수

## 데이터베이스 마이그레이션

```bash
alembic upgrade head
```

현재 마이그레이션은 사용자·관심종목, 뉴스, 뉴스 한국어 요약·카테고리 스키마를 포함합니다.
로컬 앱은 실행 편의를 위해 누락된 테이블을 자동 생성하지만, 배포 환경에서는 애플리케이션
시작 전에 Alembic을 실행하는 구성이 필요합니다.

## Docker 실행

Docker Compose는 PostgreSQL, Redis, FastAPI, Celery worker와 Celery Beat를 실행합니다.

```bash
cp .env.example .env
docker compose up --build
```

Docker 대시보드는 <http://localhost:8000>에서 확인합니다.

## 테스트와 품질 확인

```bash
ruff check .
pytest -q
node --check app/static/app.js
git diff --check
```

테스트에서는 환경 변수를 Mock provider로 덮어쓰고 메모리 SQLite를 사용하므로 실제 API를
호출하거나 로컬 `stock_briefing.db`를 변경하지 않습니다. 현재 테스트 범위에는 관심 종목
CRUD, 토스 응답 매핑과 토큰 재사용, 뉴스 중복 제거, FRED·Alpha Vantage 응답 파싱,
브리핑 기사 선택 로직이 포함됩니다.

## 보안 원칙

- `.env`, Client Secret과 API 키를 커밋하지 않습니다.
- 토스증권 액세스 토큰은 메모리에만 캐시하고 DB나 로그에 저장하지 않습니다.
- Gemini 프롬프트에 증권사 인증정보나 개인 금융정보를 포함하지 않습니다.
- 현재 데모는 고정 사용자로 동작하므로 인터넷에 그대로 공개하지 않습니다.
- 실제 배포 전 로그인, 사용자별 데이터 격리, 암호화된 비밀 저장소와 HTTPS가 필요합니다.

## 현재 제한과 다음 단계

- KOSPI/KOSDAQ, NASDAQ, S&P 500 지수 카드와 포트폴리오 구성은 아직 샘플입니다.
- 미국장 상태는 현재 정적 표시이며 휴장일·프리마켓·애프터마켓 계산이 필요합니다.
- Alpha Vantage 기사만으로는 원화·국내시장 뉴스가 부족할 수 있어 국내 뉴스/RSS 공급자
  확장이 필요합니다.
- 오늘의 포커스는 수치와 관련 기사를 함께 보여주지만 기사를 가격 변화의 확정적 원인으로
  단정하지 않습니다.
- 07:30 Celery 브리핑 작업은 아직 placeholder이며 브리핑 저장 이력도 구현되지 않았습니다.
- 토스 API 장애에 대비한 최근 정상 가격 캐시가 필요합니다.
- 실제 보유 종목 자동 동기화, 사용자 로그인과 공개 데모 배포가 다음 주요 목표입니다.

## 외부 서비스와 비용

Mock 모드는 별도 결제 없이 실행됩니다. Gemini, Alpha Vantage와 토스증권 API의 무료 제공
범위, 호출 한도와 이용 조건은 각 서비스 정책에 따라 달라질 수 있습니다. 실제 배포 전에는
각 공식 문서에서 현재 요금과 제한을 확인해야 합니다.

## 공식 데이터·API 문서

- [토스증권 Open API](https://developers.tossinvest.com/docs)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [FRED 미국 10년물 국채 금리 DGS10](https://fred.stlouisfed.org/series/DGS10)
