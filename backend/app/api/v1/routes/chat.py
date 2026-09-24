from fastapi import APIRouter

from app.schemas.chat import RecomendacionRequest, RecomendacionResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat/recomendar", response_model=RecomendacionResponse)
async def recomendar_ruta(payload: RecomendacionRequest) -> RecomendacionResponse:
    service = RecommendationService()
    return await service.create_recommendation(payload)
