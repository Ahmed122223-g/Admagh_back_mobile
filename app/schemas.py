from __future__ import annotations
from datetime import datetime
from typing import List, Optional, ClassVar

from pydantic import BaseModel, EmailStr, Field

# --- نماذج المصادقة (Auth) ---


class UserBase(BaseModel):
    name: str
    email: EmailStr
    premium_plan: Optional[str] = None  # إضافة حقل الخطة المميزة


class UserCreate(UserBase):
    password: str 
    

class UserRead(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    verification_token: Optional[str] = None
    is_unlocked: bool = False
    plan: Optional[str] = None
    subscription_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_premium: bool = False  
    premium_plan: Optional[str] = None 
    created_at: datetime

    model_config = {
        "from_attributes": True
    }



class SubscriptionUpdate(BaseModel):
    plan: str
    is_premium: Optional[bool] = None
    subscription_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class ActivationCodeRequest(BaseModel):
    code: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    id: Optional[int] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class FirebaseTokenRequest(BaseModel):
    id_token: str


class GoogleTokenRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class CalendarStatusResponse(BaseModel):
    is_linked: bool
    email: Optional[str] = None


class CalendarEventRequest(BaseModel):
    start_time: str  # HH:MM format


class CalendarEventUpdate(BaseModel):
    completed: Optional[bool] = None


class CalendarEventResponse(BaseModel):
    event_id: str
    start_datetime: datetime
    end_datetime: datetime


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

class VerifyResetCode(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "متوسطة"
    due_date: Optional[datetime] = None
    category: str = "عام"
    estimated_hours: float = 1.0


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    status: str = "لم تبدأ"
    completed: bool = False

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None


class TaskRead(TaskUpdate):
    id: int
    owner_id: int
    created_at: datetime
    is_active: bool
    remaining_time_seconds: int
    time_spent_seconds: int
    start_time: Optional[datetime] = None
    initial_duration_seconds: int
    model_config = {
        "from_attributes": True
    }


class TaskTimerAction(BaseModel):
    progress_details: Optional[str] = None


class NoteBase(BaseModel):
    title: str = "ملاحظة جديدة"
    content: str = ""
    category: str = "أفكار"
    is_starred: bool = False

class NoteCreate(NoteBase):
    pass


class NoteUpdate(NoteBase):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_starred: Optional[bool] = None


class NoteRead(NoteBase):
    id: int
    owner_id: int
    created_at: datetime
    model_config = {
        "from_attributes": True
    }


# --- نماذج الأصدقاء (Friends) ---

class FriendshipBase(BaseModel):
    user_id: int
    friend_id: int
    status: str

class FriendshipCreate(BaseModel):
    friend_id: int # The ID of the user to send a request to

class FriendshipRead(FriendshipBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class FriendRequest(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class Friend(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }

class SubscriptionUpdate(BaseModel):
    plan: str
    is_premium: Optional[bool] = None
    subscription_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class ActivationCodeRequest(BaseModel):
    code: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    id: Optional[int] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class FirebaseTokenRequest(BaseModel):
    id_token: str


class GoogleTokenRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class CalendarStatusResponse(BaseModel):
    is_linked: bool
    email: Optional[str] = None


class CalendarEventRequest(BaseModel):
    start_time: str  # HH:MM format


class CalendarEventUpdate(BaseModel):
    completed: Optional[bool] = None


class CalendarEventResponse(BaseModel):
    event_id: str
    start_datetime: datetime
    end_datetime: datetime


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

class VerifyResetCode(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "متوسطة"
    due_date: Optional[datetime] = None
    category: str = "عام"
    estimated_hours: float = 1.0


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    status: str = "لم تبدأ"
    completed: bool = False

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None


class TaskRead(TaskUpdate):
    id: int
    owner_id: int
    created_at: datetime
    is_active: bool
    remaining_time_seconds: int
    time_spent_seconds: int
    start_time: Optional[datetime] = None
    initial_duration_seconds: int
    model_config = {
        "from_attributes": True
    }


class TaskTimerAction(BaseModel):
    progress_details: Optional[str] = None


class NoteBase(BaseModel):
    title: str = "ملاحظة جديدة"
    content: str = ""
    category: str = "أفكار"
    is_starred: bool = False

class NoteCreate(NoteBase):
    pass


class NoteUpdate(NoteBase):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_starred: Optional[bool] = None


class NoteRead(NoteBase):
    id: int
    owner_id: int
    created_at: datetime
    model_config = {
        "from_attributes": True
    }


# --- نماذج الأصدقاء (Friends) ---

class FriendshipBase(BaseModel):
    user_id: int
    friend_id: int
    status: str

class FriendshipCreate(BaseModel):
    friend_id: int # The ID of the user to send a request to

class FriendshipRead(FriendshipBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class FriendRequest(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class Friend(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }

class UserSearchRead(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }
