import json

from google import genai
from google.genai import types

from app.schemas.news import (
    NewsAnalysisRequest,
    NewsAnalysisResult,
    NewsEnrichmentBatch,
)


class GeminiNewsAnalyzer:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def analyze(self, payload: NewsAnalysisRequest) -> NewsAnalysisResult:
        prompt = f"""
다음 공개 뉴스 기사를 한국어로 분석하세요.

규칙:
- 기사에 명시된 사실과 추론을 분리하세요.
- 주가 방향을 예측하거나 매수·매도 조언을 하지 마세요.
- candidate_symbols 중 기사와 직접 관련된 종목만 related_symbols에 포함하세요.
- 근거가 부족한 내용은 uncertainties에 적으세요.
- 기사에 없는 수치나 사건을 만들어내지 마세요.

제목: {payload.title}
후보 종목: {", ".join(payload.candidate_symbols) or "없음"}
원문 URL: {payload.source_url or "없음"}
기사 본문:
{payload.content}
""".strip()

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NewsAnalysisResult,
            ),
        )
        result = NewsAnalysisResult.model_validate_json(response.text)
        return result.model_copy(update={"provider": "gemini"})

    def enrich(self, articles: list[dict[str, str | int]]) -> NewsEnrichmentBatch:
        prompt = f"""
다음 공개 뉴스 목록을 한국어로 요약하고 카테고리를 분류하세요.

규칙:
- 각 index를 빠짐없이 그대로 반환하세요.
- content_source가 extracted_body이면 추출 본문을, provider_summary이면 뉴스 제공자의 요약을
  근거로 사용하세요.
- korean_summary는 content에 있는 사실만 사용해 2~3문장으로 작성하세요.
- 수치, 회사명, 사건을 임의로 만들지 마세요.
- 투자 권유나 주가 방향 예측을 하지 마세요.
- category는 금리, 환율, 반도체, 실적, 전쟁·지정학, 기업, 기타 중 하나입니다.

기사 목록:
{json.dumps(articles, ensure_ascii=False)}
""".strip()
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NewsEnrichmentBatch,
            ),
        )
        return NewsEnrichmentBatch.model_validate_json(response.text)
