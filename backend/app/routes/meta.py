from fastapi import APIRouter, Depends

from app.dependencies import get_triage_service
from app.schemas import ProvidersMeta
from app.services.triage_service import TriageService

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers", response_model=ProvidersMeta)
def providers(triage: TriageService = Depends(get_triage_service)) -> ProvidersMeta:
    return ProvidersMeta.model_validate(triage.meta())
