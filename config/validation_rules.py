"""
NOTE: This module is currently unused (services/validation_service.py
validates against core.feature_schema.FEATURE_SCHEMA directly, not
against this file). It is kept here, updated to match the real model
feature names, in case something re-adopts it later - update
FEATURE_SCHEMA in core/feature_schema.py first if you need to change
validation behavior for the live app.
"""

VALIDATION_RULES = {

    "age": {
        "type": int,
        "min": 10,
        "max": 100,
        "required": True
    },

    "total_screen_min": {
        "type": float,
        "min": 0,
        "max": 1440,
        "required": True
    },

    "sleep_hours": {
        "type": float,
        "min": 0,
        "max": 15,
        "required": True
    },

    "gender": {
        "type": str,
        "choices": [
            "Female",
            "Male",
            "Non-binary",
            "Unknown",
        ]
    }

}
