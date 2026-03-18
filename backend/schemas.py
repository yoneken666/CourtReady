from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- CASE SCHEMAS ---

class CaseIntake(BaseModel):
    caseTitle: str
    caseType: str
    caseDescription: str

class CaseResponse(BaseModel):
    id: int
    caseTitle: str
    caseType: str
    caseDescription: str
    owner_email: str

    class Config:
        from_attributes = True

# --- ANALYSIS SCHEMAS ---

class AnalysisRequest(BaseModel):
    caseTitle: str
    caseType: str
    caseDescription: str

class RelevantLaw(BaseModel):
    source_text: str
    relevance_score: float
    source_category: str

class ValidityAssessment(BaseModel):
    risk_level: str
    advice_summary: str
    simplified_advice: str

class AnalysisResponse(BaseModel):
    case_summary: str
    key_facts: List[str]
    relevant_laws: List[RelevantLaw]
    validity_status: str
    validity_assessment: ValidityAssessment

# --- CASE MATCHING SCHEMAS ---

class CaseMatchResult(BaseModel):
    case_label: str              # human-readable: court, year, parties
    source_file: str             # original PDF filename
    similarity_percentage: float
    relevance: str               # "supports" | "opposes" | "neutral"
    explanation: str

class CaseMatchResponse(BaseModel):
    top_matches: List[CaseMatchResult]
    message: str
