"""api/schemas/demo.py"""

from __future__ import annotations

from pydantic import BaseModel

from api.schemas.prediction import PredictResponse


class DemoPopulateResponse(BaseModel):
    days_created: int
    friend_connected: bool
    final_result: PredictResponse
    final_user_data: dict
