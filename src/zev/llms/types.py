from typing import List, Optional

from pydantic import BaseModel


class Command(BaseModel):
    command: str
    short_explanation: str
    is_dangerous: bool
    dangerous_explanation: Optional[str] = None


class OptionsResponse(BaseModel):
    commands: List[Command]
    is_valid: bool
    explanation_if_not_valid: Optional[str] = None
