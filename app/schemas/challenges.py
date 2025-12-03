from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# --- Question Schemas ---
class QuestionOptionCreate(BaseModel):
    text: str
    is_correct: bool = False

class QuestionOptionResponse(QuestionOptionCreate):
    id: int
    
    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    text: str
    type: str # 'mcq', 'true_false'
    explanation: Optional[str] = None
    options: List[QuestionOptionCreate]

class QuestionResponse(QuestionCreate):
    id: int
    options: List[QuestionOptionResponse]

    class Config:
        from_attributes = True

# --- Quiz Schemas ---
class QuizCreate(BaseModel):
    duration_minutes: int
    questions: List[QuestionCreate]

class QuizResponse(BaseModel):
    id: int
    duration_minutes: int
    questions: List[QuestionResponse]

    class Config:
        from_attributes = True

# --- Participant Schemas ---
class ParticipantResponse(BaseModel):
    id: int
    user_id: int
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    score: Optional[float] = None
    user_name: Optional[str] = None # Helper to show name

    class Config:
        from_attributes = True

# --- Challenge Schemas ---
class ChallengeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    is_quiz: bool = False
    lifespan_hours: int = 24
    invited_friend_ids: List[int]
    quiz_data: Optional[QuizCreate] = None # Required if is_quiz is True

class ChallengeResponse(BaseModel):
    id: int
    creator_id: int
    name: str
    description: Optional[str]
    duration_minutes: int
    is_quiz: bool
    lifespan_hours: int
    created_at: datetime
    expires_at: datetime
    participants: List[ParticipantResponse]
    quiz: Optional[QuizResponse] = None

    class Config:
        from_attributes = True

class ChallengeListResponse(BaseModel):
    id: int
    name: str
    status: str # 'active', 'expired', 'completed'
    is_quiz: bool
    created_at: datetime
    expires_at: datetime
    my_status: Optional[str] # 'invited', 'accepted', 'completed'

    class Config:
        from_attributes = True

# --- Submission Schemas ---
class AnswerSubmission(BaseModel):
    question_id: int
    selected_option_id: int

class ChallengeSubmission(BaseModel):
    answers: List[AnswerSubmission] = []
