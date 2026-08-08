"""
api/routers/persona.py
--------------------------
Assigns a behavioral-persona cluster (from the unsupervised KMeans
model in PersonaService, independent of the risk classifier) for a
given day's feature values. Validation runs through the same
ValidationService every other input-taking endpoint uses, so the
persona model never sees an out-of-range or malformed value.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_persona_service, get_validation_service
from api.exceptions.errors import DomainValidationError
from api.schemas.persona import PersonaRequest, PersonaResponse
from services.account_service import Account
from services.persona_service import PersonaService
from services.validation_service import ValidationService

router = APIRouter(prefix="/personas", tags=["Personas"])


@router.post(
    "/assign", response_model=PersonaResponse,
    summary="Assign the nearest behavioral-persona cluster for a given day's feature values",
)
def assign_persona(
    payload: PersonaRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    persona_service: PersonaService = Depends(get_persona_service),
) -> PersonaResponse:
    validation = validator.validate(payload.user_data)
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)

    result = persona_service.assign(validation.cleaned_data)
    return PersonaResponse.from_persona_result(result)
