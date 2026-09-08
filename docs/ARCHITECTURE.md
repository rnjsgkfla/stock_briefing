# Architecture

Morning Bell은 한국·미국 주식 투자자가 아침에 밤사이 미국 시장과 관심 종목을 빠르게
훑는 서비스다. 미국주식 보유자에게는 수면 시간의 공백을, 한국주식 보유자에게는 미국장과
환율·업종 흐름이 국내장 시가에 미칠 정보 공백을 줄인다. 현재 범위는 정보 요약이며 주문
실행이나 투자 추천은 포함하지 않는다.

## 요청 흐름

```text
Browser
  ├─ GET /api/v1/dashboard  ──> MarketDataService (sample adapter)
  ├─ CRUD /api/v1/watchlist ──> Toss Invest stock info + prices ─> DB
  ├─ GET /api/v1/broker/accounts ─> Toss Invest OAuth ─> account sequence
  ├─ GET /api/v1/broker/holdings ─> account header ─> KR·US holdings
  ├─ POST /api/v1/news/refresh ─> Alpha Vantage ─> deduplicate
  │                                      └───────> Trafilatura body extraction
  │                                                   ├─ success: extracted body
  │                                                   └─ failure: provider summary
  │                                                            └─> Gemini summary/category ─> DB
  ├─ GET /api/v1/news/latest ──> categorized overnight news
  └─ GET /api/v1/dashboard ────> Toss account holdings/prices/FX/KR indices
                                 + FRED DGS10/US indices + stored news

Celery Beat (07:10 KST) ──> Celery Worker ──> news collection
Celery Beat (07:30 KST) ──> Celery Worker ──> briefing pipeline (next phase)
                                 │
                                 └──────────── Redis broker
```

## 설계 결정

- 로컬 기본 DB는 별도 설치가 필요 없는 SQLite로 두고, Docker 환경에서는 PostgreSQL을 쓴다.
- AI 제공자는 `mock`과 `gemini`를 동일한 응답 스키마로 감싸 키 없이도 테스트 가능하다.
- 뉴스의 사실, 해석, 불확실성을 분리해 환각과 투자 조언 위험을 낮춘다.
- 최신 미요약 기사 중 최대 10건만 동시에 3개씩 본문 추출한다. 원문은 저장하지 않고 추출
  상태와 본문 해시만 남기며, 실패하면 뉴스 provider 요약을 사용한다.
- 본문 URL은 HTTP(S)와 표준 포트만 허용하고 내부 IP, 3회를 넘는 리다이렉트, 1.5MB를 넘는
  응답과 비 HTML 콘텐츠를 차단한다.
- 데모 사용자를 고정해 인증 없이 핵심 CRUD를 보여준다. 실제 배포 전에는 OAuth/JWT 경계를
  추가하고 모든 쿼리를 인증 사용자 ID로 제한해야 한다.
- Toss 모드에서는 설정 계좌 또는 첫 번째 계좌를 선택해 실제 보유 종목을 읽는다. 국내·미국
  종목의 비중은 통화 혼합을 피하기 위해 각 시장 그룹 안에서 계산하고, 전체 일일 손익률은
  토스증권의 원화 환산 요약값을 사용한다. 빈 계좌는 정상 상태로 유지하며 데모 화면은 사용자가
  명시적으로 전환했을 때만 표시한다.
- 오늘의 포커스는 미국·국내 지수 등락률, 반도체 종목 평균 등락률, 미국 10년물 금리 변화폭,
  USD/KRW 등락률과 실적·지정학 뉴스 건수를 비교해 상위 3개를 선택한다. 선택된 항목의 상세
  설명에는 실제 수치, 기준일과 저장된 한국어 뉴스 요약을 함께 제공한다. 과거 뉴스가 오늘의
  이슈로 다시 선택되지 않도록 평일 36시간, 월요일 72시간 범위만 선정 근거에 포함한다.
- 관심 종목과 국내 지수 현재가는 Mock 또는 토스증권 Open API를 선택하며 액세스 토큰은 만료
  직전까지 메모리에 캐시한다. 미국 지수는 FRED의 최근 거래일 종가를 사용한다. 뉴스는 Mock
  또는 Alpha Vantage 수집기를 선택하고 URL 해시를 외부 ID로 사용해 중복 저장을 막는다.
- 토스증권 연동은 조회 전용이다. Client Secret과 액세스 토큰을 DB에 저장하거나 Gemini
  프롬프트로 전달하지 않는다.

## 다음 경계

1. 시세 공급자 장애 시 최근 정상 가격 캐시 fallback
2. 국내외 공식 RSS/API 뉴스 수집 범위 확대
3. 사용자별 브리핑 저장 및 생성 상태 조회
4. OAuth 로그인과 사용자별 인증정보 암호화 저장
5. OpenTelemetry/Sentry 기반 관측성 및 배포 환경 분리
