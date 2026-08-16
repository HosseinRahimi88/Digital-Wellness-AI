"""
Validation DTO
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    """
    Result returned by ValidationService.
    """

    is_valid: bool

    cleaned_data: dict[str, Any] = field(default_factory=dict)

    errors: dict[str, str] = field(default_factory=dict)

    warnings: dict[str, str] = field(default_factory=dict)