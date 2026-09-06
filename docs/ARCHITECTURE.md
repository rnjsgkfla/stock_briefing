# Architecture

Morning Bell은 한국·미국 주식 투자자가 아침에 밤사이 미국 시장과 관심 종목을 빠르게
훑는 서비스다. 미국주식 보유자에게는 수면 시간의 공백을, 한국주식 보유자에게는 미국장과
환율·업종 흐름이 국내장 시가에 미칠 정보 공백을 줄인다. 현재 범위는 정보 요약이며 주문
실행이나 투자 추천은 포함하지 않는다.

## 요청 흐름

```text
Browser
  ├─ GET /api/v1/dashboard  ──> MarketDataService (sample adapter)
  ├─ CRUD /api/v1/watchlist ──> SQLAlchemy ──> SQLite / PostgreSQL
  └─ POST /api/v1/news/analyze ─> NewsAnalysisService ─> Mock / Gemini

Celery Beat (07:30 KST) ──> Celery Worker ──> briefing pipeline (next phase)
                                 │
                                 └──────────── Redis broker
```

## 설계 결정

- 로컬 기본 DB는 별도 설치가 필요 없는 SQLite로 두고, Docker 환경에서는 PostgreSQL을 쓴다.
- AI 제공자는 `mock`과 `gemini`를 동일한 응답 스키마로 감싸 키 없이도 테스트 가능하다.
- 뉴스의 사실, 해석, 불확실성을 분리해 환각과 투자 조언 위험을 낮춘다.
- 데모 사용자를 고정해 인증 없이 핵심 CRUD를 보여준다. 실제 배포 전에는 OAuth/JWT 경계를
  추가하고 모든 쿼리를 인증 사용자 ID로 제한해야 한다.
- 시세와 시장 요약은 현재 미국 종목 중심의 sample adapter다. 뉴스도 자동 수집하지 않고
  사용자가 입력한 공개 기사만 분석한다. 실제 공급자 연결 시 서비스 인터페이스 안쪽만
  교체하고 API 응답은 유지한다.

## 다음 경계

1. 미국 시세·뉴스 API와 국내 시세 API adapter, 실패 시 캐시 fallback
2. 국내외 공식 RSS/API 뉴스 수집, URL 기준 중복 제거, 원문 출처 저장
3. 사용자별 브리핑 저장 및 생성 상태 조회
4. OAuth 로그인과 암호화된 증권사 연동 토큰 저장
5. OpenTelemetry/Sentry 기반 관측성 및 배포 환경 분리
