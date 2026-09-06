import asyncio

from app.core.config import get_settings
from app.integrations.gemini import GeminiNewsAnalyzer
from app.schemas.news import NewsAnalysisRequest, NewsAnalysisResult


async def analyze_public_news(payload: NewsAnalysisRequest) -> NewsAnalysisResult:
    settings = get_settings()

    if settings.ai_provider == "mock":
        return NewsAnalysisResult(
            summary=f"[Mock] {payload.title}",
            related_symbols=payload.candidate_symbols,
            impact_direction="neutral",
            importance="medium",
            facts=["Mock 모드에서는 실제 기사 분석을 수행하지 않습니다."],
            interpretation="Gemini API 키를 설정하면 실제 분석 결과로 대체됩니다.",
            uncertainties=["현재 결과는 개발용 고정 응답입니다."],
            provider="mock",
        )

    api_key = settings.gemini_api_key
    if api_key is None or not api_key.get_secret_value():
        raise RuntimeError("AI_PROVIDER=gemini일 때 GEMINI_API_KEY가 필요합니다.")

    analyzer = GeminiNewsAnalyzer(
        api_key=api_key.get_secret_value(),
        model=settings.gemini_model,
    )
    return await asyncio.to_thread(analyzer.analyze, payload)
