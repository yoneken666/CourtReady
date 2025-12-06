from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import List, Optional
import re

# ... (User schemas remain the same) ...
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v): raise ValueError("Need uppercase")
        if not re.search(r"[a-z]", v): raise ValueError("Need lowercase")
        if not re.search(r"[0-9]", v): raise ValueError("Need digit")
        if not re.search(r"[!@#$%^&*(),.?:{}|<>_~-]", v): raise ValueError("Need special char")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CaseIntake(BaseModel):
    caseTitle: str
    caseType: str
    caseDescription: str

# --- NEW: AI Response Models ---
class CaseMatch(BaseModel):
    preview: str
    full_text: str

class CaseAnalysisResponse(BaseModel):
    status: str
    analysis: Optional[str] = None
    matches: Optional[List[CaseMatch]] = []
    message: Optional[str] = None

class CaseResponse(CaseIntake):
    id: int
    owner_email: str
    # Add AI analysis to the response
    ai_analysis: Optional[CaseAnalysisResponse] = None

    class Config:
        from_attributes = True