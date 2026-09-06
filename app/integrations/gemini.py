from google import genai

from app.schemas.news import NewsAnalysisRequest, NewsAnalysisResult


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

        interaction = self._client.interactions.create(
            model=self._model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": NewsAnalysisResult.model_json_schema(),
            },
        )
        result = NewsAnalysisResult.model_validate_json(interaction.output_text)
        return result.model_copy(update={"provider": "gemini"})
